from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import (
    blacklist_token,
    get_identity_from_request,
    is_rate_limited,
    is_token_blacklisted,
    record_audit_event,
)
from app.models import User
from app.schemas import AuthResponse, RefreshRequest, TokenPair, UserCreate, UserLogin, UserOut

router = APIRouter(tags=["auth"])

RATE_LIMIT_WINDOW = settings.auth_rate_limit_window_seconds
RATE_LIMIT_LOGIN = settings.auth_rate_limit_login
RATE_LIMIT_REGISTER = settings.auth_rate_limit_register

_ACCESS_MAX_AGE = settings.access_token_expire_minutes * 60
_REFRESH_MAX_AGE = settings.refresh_token_expire_days * 86400


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Set HttpOnly, Secure, SameSite=Strict cookies for both tokens."""
    is_secure = settings.environment != "development"
    cookie_kwargs: dict = dict(
        httponly=True,
        secure=is_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie("access_token", access_token, max_age=_ACCESS_MAX_AGE, **cookie_kwargs)
    response.set_cookie("refresh_token", refresh_token, max_age=_REFRESH_MAX_AGE, **cookie_kwargs)


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, response: Response, db: Session = Depends(get_db)):
    identity = get_identity_from_request(request)
    try:
        if is_rate_limited("register", identity, RATE_LIMIT_REGISTER, RATE_LIMIT_WINDOW):
            raise HTTPException(status_code=429, detail="Too many registration attempts")
    except HTTPException:
        raise
    except Exception:
        pass

    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    if payload.email and db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already exists")

    user = User(
        username=payload.username.strip(),
        email=str(payload.email).strip() if payload.email else "",
        password=security.hash_password(payload.password),
        first_name="",
        last_name="",
        is_staff=False,
        is_superuser=False,
        is_active=True,
        date_joined=datetime.now(timezone.utc),
    )
    db.add(user)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(user)

    access_token, _ = security.create_access_token(str(user.id), user.username, user.email)
    refresh_token, _, _ = security.create_refresh_token(str(user.id))

    _set_auth_cookies(response, access_token, refresh_token)
    record_audit_event({"action": "register", "user_id": user.id, "ip": identity})

    return AuthResponse(
        user=UserOut(id=user.id, username=user.username, email=user.email, created_at=user.date_joined),
        tokens=TokenPair(access_token=access_token, refresh_token=refresh_token),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    identity = get_identity_from_request(request)
    try:
        if is_rate_limited("login", identity, RATE_LIMIT_LOGIN, RATE_LIMIT_WINDOW):
            raise HTTPException(status_code=429, detail="Too many login attempts")
    except HTTPException:
        raise
    except Exception:
        pass

    try:
        user_query = db.query(User)
        user = None
        if payload.username:
            user = user_query.filter(User.username == payload.username.strip()).first()
        if user is None and payload.email:
            user = user_query.filter(User.email == str(payload.email).strip()).first()
    except SQLAlchemyError:
        db.rollback()
        raise

    if user is None or not security.verify_password(payload.password, user.password):
        record_audit_event({"action": "login_failed", "user_id": user.id if user else None, "ip": identity})
        return JSONResponse(
            status_code=401,
            content={
                "error": "authentication_failed",
                "message": "Invalid email or password",
            },
        )

    access_token, _ = security.create_access_token(str(user.id), user.username, user.email)
    refresh_token, _, _ = security.create_refresh_token(str(user.id))

    _set_auth_cookies(response, access_token, refresh_token)
    try:
        record_audit_event({"action": "login_success", "user_id": user.id, "ip": identity})
    except Exception:
        pass

    return AuthResponse(
        user=UserOut(id=user.id, username=user.username, email=user.email, created_at=user.date_joined),
        tokens=TokenPair(access_token=access_token, refresh_token=refresh_token),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    # Try cookie first, then JSON body
    from fastapi import Cookie as CookieParam
    raw_token: str | None = request.cookies.get("refresh_token")
    if not raw_token:
        try:
            import asyncio
            body = asyncio.get_event_loop().run_until_complete(request.json())
            raw_token = body.get("refresh_token")
        except Exception:
            pass
    if not raw_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        claims = security.decode_token(raw_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    if claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    jti = claims.get("jti")
    user_id = claims.get("sub")
    if not jti or not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if is_token_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    if datetime.fromtimestamp(claims.get("exp", 0), tz=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    access_token, _ = security.create_access_token(str(user.id), user.username, user.email)
    new_refresh_token, _, _ = security.create_refresh_token(str(user.id))

    # Blacklist old refresh JTI
    remaining_ttl = int(claims.get("exp", 0)) - int(datetime.now(timezone.utc).timestamp())
    if remaining_ttl > 0:
        blacklist_token(jti, remaining_ttl)

    _set_auth_cookies(response, access_token, new_refresh_token)
    return TokenPair(access_token=access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserOut)
def me(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip() or None
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        claims = security.decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    if claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")

    jti = claims.get("jti")
    if jti and is_token_blacklisted(jti):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(id=user.id, username=user.username, email=user.email, created_at=user.date_joined)


@router.post("/logout")
def logout(request: Request, response: Response):
    # Blacklist access token JTI
    access_token = request.cookies.get("access_token") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip() or None
    if access_token:
        try:
            claims = security.decode_token(access_token)
            jti = claims.get("jti")
            exp = int(claims.get("exp", 0))
            remaining = exp - int(datetime.now(timezone.utc).timestamp())
            if jti and remaining > 0:
                blacklist_token(jti, remaining)
        except Exception:
            pass

    # Blacklist refresh token JTI
    refresh_token_cookie = request.cookies.get("refresh_token")
    if refresh_token_cookie:
        try:
            claims = security.decode_token(refresh_token_cookie)
            jti = claims.get("jti")
            exp = int(claims.get("exp", 0))
            remaining = exp - int(datetime.now(timezone.utc).timestamp())
            if jti and remaining > 0:
                blacklist_token(jti, remaining)
        except Exception:
            pass

    _clear_auth_cookies(response)
    return {"ok": True, "message": "Logged out successfully"}
