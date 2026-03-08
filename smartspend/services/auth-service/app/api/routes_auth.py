from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..core import security
from ..core.config import settings
from ..core.database import get_db
from ..core.redis import is_rate_limited, record_audit_event
from ..models import User
from ..schemas import AuthResponse, RefreshRequest, TokenPair, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

RATE_LIMIT_WINDOW = settings.auth_rate_limit_window_seconds
RATE_LIMIT_LOGIN = settings.auth_rate_limit_login
RATE_LIMIT_REGISTER = settings.auth_rate_limit_register


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, request: Request, db: Session = Depends(get_db)):
    identity = request.client.host if request.client else "unknown"
    if is_rate_limited("register", identity, RATE_LIMIT_REGISTER, RATE_LIMIT_WINDOW):
        raise HTTPException(status_code=429, detail="Too many registration attempts")

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
    db.commit()
    db.refresh(user)

    access_token = security.create_access_token(str(user.id), user.username, user.email)
    refresh_token = security.create_refresh_token(str(user.id))[0]

    record_audit_event({"action": "register", "user_id": user.id, "ip": identity})

    return AuthResponse(
        user=UserOut(id=user.id, username=user.username, email=user.email, created_at=user.date_joined),
        tokens=TokenPair(access_token=access_token, refresh_token=refresh_token),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    identity = request.client.host if request.client else "unknown"
    if is_rate_limited("login", identity, RATE_LIMIT_LOGIN, RATE_LIMIT_WINDOW):
        raise HTTPException(status_code=429, detail="Too many login attempts")

    user_query = db.query(User)
    user = None
    if payload.username:
        user = user_query.filter(User.username == payload.username.strip()).first()
    if user is None and payload.email:
        user = user_query.filter(User.email == str(payload.email).strip()).first()

    if user is None or not security.verify_password(payload.password, user.password):
        record_audit_event({"action": "login_failed", "user_id": user.id if user else None, "ip": identity})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = security.create_access_token(str(user.id), user.username, user.email)
    refresh_token = security.create_refresh_token(str(user.id))[0]

    record_audit_event({"action": "login_success", "user_id": user.id, "ip": identity})

    return AuthResponse(
        user=UserOut(id=user.id, username=user.username, email=user.email, created_at=user.date_joined),
        tokens=TokenPair(access_token=access_token, refresh_token=refresh_token),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        claims = security.decode_token(payload.refresh_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    if claims.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    jti = claims.get("jti")
    user_id = claims.get("sub")
    if not jti or not user_id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if datetime.fromtimestamp(claims.get("exp", 0), tz=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    access_token = security.create_access_token(str(user.id), user.username, user.email)
    refresh_token = security.create_refresh_token(str(user.id))[0]

    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserOut)
def me(token: str = Depends(security.oauth2_scheme), db: Session = Depends(get_db)):
    try:
        claims = security.decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    if claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserOut(id=user.id, username=user.username, email=user.email, created_at=user.date_joined)


@router.post("/logout")
def logout(_: RefreshRequest | None = None, __: str = Depends(security.oauth2_scheme)):
    return {"ok": True}
