from __future__ import annotations

import time

import redis

from .config import settings


_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
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
    key = f"rl:{scope}:{identity}"
    client = get_redis()
    pipeline = client.pipeline()
    pipeline.incr(key, 1)
    pipeline.ttl(key)
    count, ttl = pipeline.execute()
    if ttl == -1:
        client.expire(key, window_seconds)
    return int(count) > limit


def record_audit_event(event: dict) -> None:
    client = get_redis()
    payload = {"ts": int(time.time()), **event}
    client.lpush("auth:audit", str(payload))
    client.ltrim("auth:audit", 0, 999)


def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Add a JWT JTI to the Redis blacklist with TTL matching token expiry."""
    client = get_redis()
    client.setex(f"bl:jti:{jti}", ttl_seconds, "1")


def is_token_blacklisted(jti: str) -> bool:
    """Return True if the given JTI has been blacklisted (i.e. logged out)."""
    client = get_redis()
    return client.exists(f"bl:jti:{jti}") == 1
