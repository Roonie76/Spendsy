from __future__ import annotations

from fastapi import Header, HTTPException, status
from app.core.config import settings

def verify_internal_api_key(x_internal_api_key: str = Header(None)) -> None:
    """
    Verify the internal API key for inter-service communication.
    """
    if not settings.internal_api_key:
        # In case the key is not set, we might want to block all requests in prod
        # but allow in dev. For now, let's assume it MUST be set.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal API key not configured",
        )
    
    if x_internal_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal API key",
        )
    return None
