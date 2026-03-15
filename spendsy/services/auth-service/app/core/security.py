from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from app.core.config import settings
from app.core.redis import is_token_blacklisted

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    from passlib.hash import django_pbkdf2_sha256
    return django_pbkdf2_sha256.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    from passlib.hash import django_pbkdf2_sha256
    return django_pbkdf2_sha256.verify(password, password_hash)


def create_access_token(subject: str, username: str, email: str | None) -> tuple[str, str]:
    """Returns (token, jti)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    jti = uuid.uuid4().hex
    payload = {
        "sub": subject,
        "username": username,
        "email": email,
        "type": "access",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), jti


def create_refresh_token(subject: str) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    jti = uuid.uuid4().hex
    payload = {
        "sub": subject,
        "type": "refresh",
        "jti": jti,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti, expire


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def _extract_token(
    bearer: str | None,
    cookie_token: str | None,
) -> str | None:
    """Try Bearer header, then access_token cookie."""
    return bearer or cookie_token


def get_token_from_request(
    bearer: str | None = Depends(oauth2_scheme),
    access_token: str | None = Cookie(default=None),
) -> str:
    token = _extract_token(bearer, access_token)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return token
