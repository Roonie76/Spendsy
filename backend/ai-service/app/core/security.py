from __future__ import annotations

from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from app.core.config import settings
from app.core.redis import is_token_blacklisted


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@dataclass(frozen=True)
class UserContext:
    id: int
    username: str
    email: str | None


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_current_user(
    request: Request,
    bearer: str | None = Depends(oauth2_scheme),
    access_token: str | None = Cookie(default=None),
) -> UserContext:
    # Check for internal API key first
    internal_key = request.headers.get("X-Internal-API-Key")
    if internal_key and internal_key == settings.internal_api_key:
        return UserContext(id=0, username="system", email="system@spendsy.local")

    token = bearer or access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")


    user_id = payload.get("sub")
    username = payload.get("username") or ""
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return UserContext(id=int(user_id), username=username, email=payload.get("email"))
