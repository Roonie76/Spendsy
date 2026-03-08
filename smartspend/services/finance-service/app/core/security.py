from __future__ import annotations

import logging
import time
import uuid

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from .config import settings

logger = logging.getLogger("finance.security")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


class UserContext:
    __slots__ = ("id", "username", "email")

    def __init__(self, id: int, username: str, email: str | None) -> None:
        self.id = id
        self.username = username
        self.email = email


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

    user_id = payload.get("sub")
    username = payload.get("username") or ""
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")

    return UserContext(id=int(user_id), username=username, email=payload.get("email"))
