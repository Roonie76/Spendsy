from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.core.config import settings


def verify_internal_api_key(x_internal_api_key: str | None = Header(default=None, alias="X-Internal-API-Key")) -> None:
    if not settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal API key not configured")
    if not x_internal_api_key or x_internal_api_key != settings.internal_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key")
