from __future__ import annotations

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security-hardening headers to every response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[override]
        response = await call_next(request)
        
        # 1. Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # 2. Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # 3. Cross-Site Scripting (legacy but good for defense-in-depth)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # 4. Content Security Policy (Basic restrictive policy)
        # Allows self, and common CDNs if needed.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        
        # 5. Strict-Transport-Security (HSTS)
        if settings.hsts_enabled:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            
        # 6. Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response
