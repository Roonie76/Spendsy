from __future__ import annotations

import time
import logging

import redis

from app.core.config import settings

logger = logging.getLogger("auth.redis")

_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_connection_url, decode_responses=True)
    return _redis_client


def _get_client_identity(request_headers: dict, client_host: str | None) -> str:
    """Prefer X-Forwarded-For over request.client.host (fixes proxy rate-limit key)."""
    forwarded = request_headers.get("x-forwarded-for") or request_headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return client_host or "unknown"


def get_identity_from_request(request) -> str:  # type: ignore[no-untyped-def]
    """Extract real IP from FastAPI Request object, proxy-safe."""
    headers = dict(request.headers)
    host = request.client.host if request.client else None
    return _get_client_identity(headers, host)


def is_rate_limited(scope: str, identity: str, limit: int, window_seconds: int) -> bool:
    try:
        key = f"rl:{scope}:{identity}"
        client = get_redis()
        pipeline = client.pipeline()
        pipeline.incr(key, 1)
        pipeline.ttl(key)
        count, ttl = pipeline.execute()
        if ttl == -1:
            client.expire(key, window_seconds)
        return int(count) > limit
    except Exception:
        # Graceful failure: don't block requests if Redis is down
        return False


def record_audit_event(event: dict) -> None:
    try:
        client = get_redis()
        payload = {"ts": int(time.time()), **event}
        client.lpush("auth:audit", str(payload))
        client.ltrim("auth:audit", 0, 999)
    except Exception:
        logger.warning("Failed to record audit event to Redis", exc_info=True)


def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Add a JWT JTI to the Redis blacklist with TTL matching token expiry."""
    client = get_redis()
    client.setex(f"bl:jti:{jti}", ttl_seconds, "1")


def is_token_blacklisted(jti: str) -> bool:
    """Return True if the given JTI has been blacklisted (i.e. logged out)."""
    try:
        client = get_redis()
        return client.exists(f"bl:jti:{jti}") == 1
    except Exception:
        # Graceful failure: don't block auth flows if Redis is down/unreachable.
        logger.warning("token_blacklist_redis_error: jti=%s", jti)
        return False


def increment_failed_login(identity: str) -> int:
    """Increment failed login attempts for a given identity."""
    try:
        key = f"lockout:{identity}"
        client = get_redis()
        count = client.incr(key)
        if int(count) == 1:
            client.expire(key, settings.auth_lockout_window_seconds)
        return int(count)
    except Exception:
        return 0


def is_account_locked(identity: str) -> bool:
    """Check if an account/identity is currently locked out."""
    try:
        key = f"lockout:{identity}"
        client = get_redis()
        count = client.get(key)
        if count and int(count) >= settings.auth_lockout_attempts:
            return True
        return False
    except Exception:
        return False


def reset_failed_login(identity: str) -> None:
    """Reset failed login attempts for a given identity after successful login."""
    try:
        key = f"lockout:{identity}"
        client = get_redis()
        client.delete(key)
    except Exception:
        logger.warning("Failed to reset failed login counter for %s", identity, exc_info=True)
