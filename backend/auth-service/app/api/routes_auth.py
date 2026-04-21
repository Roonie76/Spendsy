from __future__ import annotations

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
import json
import uuid
import logging

logger = logging.getLogger("auth.routes")

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import (
    blacklist_token,
    get_identity_from_request,
    increment_failed_login,
    is_account_locked,
    is_rate_limited,
    is_token_blacklisted,
    record_audit_event,
    reset_failed_login,
)
from app.models import User, RefreshToken
from app.schemas import AuthResponse, RefreshRequest, TokenPair, UserCreate, UserLogin, UserOut

router = APIRouter(tags=["auth"])

RATE_LIMIT_WINDOW = settings.auth_rate_limit_window_seconds
RATE_LIMIT_LOGIN = settings.auth_rate_limit_login
RATE_LIMIT_REGISTER = settings.auth_rate_limit_register

_ACCESS_MAX_AGE = settings.access_token_expire_minutes * 60
_REFRESH_MAX_AGE = settings.refresh_token_expire_days * 86400


def _normalize_username(value: str | None) -> str:
    return (value or "").strip().lower()


def _generate_alert(
    db: Session,
    type: str,
    severity: str,
    description: str,
    actor_identity: str | None = None,
    details: dict | None = None,
) -> None:
    try:
        from app.models import SecurityAlert

        alert = SecurityAlert(
            type=type,
            severity=severity,
            description=description,
            actor_identity=actor_identity,
            details=json.dumps(details or {}),
        )
        db.add(alert)
        db.commit()
    except Exception:
        logger.warning("Failed to generate security alert: type=%s", type, exc_info=True)


def _record_audit(
    db: Session,
    request: Request,
    *,
    action: str,
    resource_type: str,
    status_code: int,
    user_id: int | None = None,
    resource_id: str = "",
    error_code: str = "",
    details: dict | None = None,
) -> None:
    try:
        from app.models import ApiAuditLog

        identity = get_identity_from_request(request)
        entry = ApiAuditLog(
            user_id=user_id,
            request_id=getattr(request.state, "request_id", None)
            or request.headers.get("X-Request-ID")
            or str(uuid.uuid4()),
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id or ""),
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            error_code=error_code,
            ip_address=identity,
            details=json.dumps(details or {}),
        )
        db.add(entry)
        db.commit()
    except Exception:
        logger.warning("Failed to record audit event: action=%s", action, exc_info=True)
        return

    try:
        # Anomaly Detection: Bruteforce-like patterns
        if action == "login_failure" and status_code == 401:
            threshold_time = datetime.utcnow() - timedelta(minutes=10)
            fail_count = (
                db.query(func.count(ApiAuditLog.id))
                .filter(
                    ApiAuditLog.ip_address == identity,
                    ApiAuditLog.action == "login_failure",
                    ApiAuditLog.created_at >= threshold_time,
                )
                .scalar()
            )

            if fail_count >= 10:
                _generate_alert(
                    db,
                    type="brute_force",
                    severity="high",
                    description=f"Persistent login failures from {identity}",
                    actor_identity=identity,
                    details={"fail_count": fail_count},
                )

        # Anomaly Detection: Account lockouts
        if action == "account_lockout":
            _generate_alert(
                db,
                type="lockout",
                severity="medium",
                description=f"Account lockout triggered for {identity}",
                actor_identity=identity,
            )
    except Exception:
        logger.warning("Failed anomaly detection in audit: action=%s", action, exc_info=True)


def _normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def _get_registration_conflict_detail(
    db: Session,
    username: str,
    email: str,
) -> str | None:
    if username and db.query(User.id).filter(func.lower(User.username) == username).first():
        return "Username already exists"
    if email and db.query(User.id).filter(func.lower(User.email) == email).first():
        return "Email already exists"
    return None


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
        logger.warning("Rate limit check failed for register, allowing request", exc_info=True)

    clean_username = _normalize_username(payload.username)
    clean_email = _normalize_email(str(payload.email) if payload.email is not None else None)

    conflict_detail = _get_registration_conflict_detail(db, clean_username, clean_email)
    if conflict_detail:
        raise HTTPException(status_code=409, detail=conflict_detail)

    user = User(
        username=clean_username,
        email=clean_email,
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
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=_get_registration_conflict_detail(db, clean_username, clean_email)
            or "Username or email already exists",
        )
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(user)

    access_token, _ = security.create_access_token(str(user.id), user.username, user.email, uid=user.uid, role=user.role)
    refresh_token, jti, expires_at = security.create_refresh_token(str(user.id))

    # Save refresh token to DB
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at))
    db.commit()

    _set_auth_cookies(response, access_token, refresh_token)
    _record_audit(db, request, action="register", resource_type="user", resource_id=str(user.id), status_code=201, user_id=user.id)

    return AuthResponse(
        user=UserOut(id=user.id, uid=user.uid, username=user.username, email=user.email, created_at=user.date_joined),
        tokens=TokenPair(access_token=access_token, refresh_token=refresh_token),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, request: Request, response: Response, db: Session = Depends(get_db)):
    identity = get_identity_from_request(request)
    if is_account_locked(identity):
        _record_audit(db, request, action="login_blocked_lockout", resource_type="user", status_code=403)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is temporarily locked due to multiple failed login attempts. Please try again later.",
        )
    try:
        if is_rate_limited("login", identity, RATE_LIMIT_LOGIN, RATE_LIMIT_WINDOW):
            raise HTTPException(status_code=429, detail="Too many login attempts")
    except HTTPException:
        raise
    except Exception:
        logger.warning("Rate limit check failed for login, allowing request", exc_info=True)

    try:
        user_query = db.query(User)
        user = None
        clean_username = _normalize_username(payload.username)
        clean_email = _normalize_email(str(payload.email) if payload.email is not None else None)
        if clean_username:
            user = user_query.filter(
                func.lower(User.username) == clean_username
            ).first()
        if user is None and clean_email:
            user = user_query.filter(
                func.lower(User.email) == clean_email
            ).first()
    except SQLAlchemyError:
        db.rollback()
        raise

    if user is None or not security.verify_password(payload.password, user.password):
        increment_failed_login(identity)
        _record_audit(db, request, action="login_failed", resource_type="user", status_code=401, user_id=user.id if user else None)
        return JSONResponse(
            status_code=401,
            content={
                "error": "authentication_failed",
                "detail": "Invalid username/email or password",
                "message": "Invalid username/email or password",
            },
        )

    reset_failed_login(identity)

    access_token, _ = security.create_access_token(str(user.id), user.username, user.email, uid=user.uid, role=user.role)
    refresh_token, jti, expires_at = security.create_refresh_token(str(user.id))

    # Save refresh token to DB
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at))
    db.commit()

    _set_auth_cookies(response, access_token, refresh_token)
    _record_audit(db, request, action="login_success", resource_type="user", resource_id=str(user.id), status_code=200, user_id=user.id)

    return AuthResponse(
        user=UserOut(id=user.id, uid=user.uid, username=user.username, email=user.email, created_at=user.date_joined),
        tokens=TokenPair(access_token=access_token, refresh_token=refresh_token),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    # Try cookie first, then JSON body
    from fastapi import Cookie as CookieParam
    raw_token: str | None = request.cookies.get("refresh_token")
    if not raw_token:
        try:
            body = await request.json()
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

    # DB verify
    db_token = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not db_token or db_token.is_revoked:
        raise HTTPException(status_code=401, detail="Refresh token has been revoked or is invalid")

    if datetime.fromtimestamp(claims.get("exp", 0), tz=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    access_token, _ = security.create_access_token(str(user.id), user.username, user.email, uid=user.uid, role=user.role)
    new_refresh_token, new_jti, new_expires_at = security.create_refresh_token(str(user.id))

    # Save new refresh token to DB and revoke old one
    db_token.is_revoked = True
    db.add(RefreshToken(user_id=user.id, jti=new_jti, expires_at=new_expires_at))
    db.commit()

    _record_audit(db, request, action="token_refresh", resource_type="user", status_code=200, user_id=user.id)

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

    return UserOut(id=user.id, uid=user.uid, username=user.username, email=user.email, created_at=user.date_joined)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    # Blacklist access token JTI
    access_token = request.cookies.get("access_token") or request.headers.get("Authorization", "").removeprefix("Bearer ").strip() or None
    user_id = None
    if access_token:
        try:
            claims = security.decode_token(access_token)
            jti = claims.get("jti")
            user_id = claims.get("sub")
            exp = int(claims.get("exp", 0))
            remaining = exp - int(datetime.now(timezone.utc).timestamp())
            if jti and remaining > 0:
                blacklist_token(jti, remaining)
        except Exception:
            logger.warning("Failed to blacklist access token on logout", exc_info=True)

    # Blacklist refresh token JTI
    refresh_token_cookie = request.cookies.get("refresh_token")
    if refresh_token_cookie:
        try:
            claims = security.decode_token(refresh_token_cookie)
            rt_jti = claims.get("jti")
            if rt_jti:
                db_token = db.query(RefreshToken).filter(RefreshToken.jti == rt_jti).first()
                if db_token:
                    db_token.is_revoked = True
                
                exp = int(claims.get("exp", 0))
                remaining = exp - int(datetime.now(timezone.utc).timestamp())
                if remaining > 0:
                    blacklist_token(rt_jti, remaining)
            db.commit()
        except Exception:
            db.rollback()

    _record_audit(db, request, action="logout", resource_type="user", status_code=200, user_id=int(user_id) if user_id else None)
    _clear_auth_cookies(response)
    return {"ok": True, "message": "Logged out successfully"}
