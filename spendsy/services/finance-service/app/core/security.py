from __future__ import annotations

import logging
import time
import uuid

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from app.core.config import settings
from app.core.redis import is_token_blacklisted

logger = logging.getLogger("finance.security")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class UserContext:
    __slots__ = ("id", "uid", "username", "email", "role")

    def __init__(self, id: int, uid: str, username: str, email: str | None, role: str = "user") -> None:
        self.id = id
        self.uid = uid
        self.username = username
        self.email = email
        self.role = role


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_current_user(
    request: Request,
    bearer: str | None = Depends(oauth2_scheme),
    access_token: str | None = Cookie(default=None),
) -> UserContext:
    token = bearer or access_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    jti = payload.get("jti")
    if jti and is_token_blacklisted(jti):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    user_id = payload.get("sub")
    uid = payload.get("uid")
    username = payload.get("username") or ""
    role = payload.get("role", "user")
    
    if not user_id or not uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    return UserContext(id=int(user_id), uid=uid, username=username, email=payload.get("email"), role=role)


class RequireRole:
    def __init__(self, allowed_roles: list[str]) -> None:
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: UserContext = Depends(get_current_user)) -> UserContext:
        if current_user.role not in self.allowed_roles:
            logger.warning(
                "rbac_denied: user_id=%s role=%s allowed=%s",
                current_user.id,
                current_user.role,
                self.allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return current_user
