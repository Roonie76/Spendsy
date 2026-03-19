from __future__ import annotations

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = logging.getLogger("finance.access")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that:
    1. Ensures every request has an X-Request-ID (generates one if absent).
    2. Logs structured access info: request_id, method, path, status_code, latency_ms, user_id.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start = time.monotonic()

        # Inject into request state for downstream handlers
        request.state.request_id = request_id

        response = await call_next(request)

        latency_ms = round((time.monotonic() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        # Best-effort extract user_id from token (no exception on failure)
        user_id: str | None = None
        try:
            from jose import jwt
            token = request.cookies.get("access_token") or \
                request.headers.get("Authorization", "").removeprefix("Bearer ").strip() or None
            if token:
                claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
                user_id = claims.get("sub")
        except Exception:
            pass

        logger.info(
            "request_id=%s method=%s path=%s status=%s latency_ms=%s user_id=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            user_id or "anonymous",
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security-hardening headers to every response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response = await call_next(request)
        
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        if settings.hsts_enabled:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response
