from __future__ import annotations

import logging
import time
import uuid

import redis as redis_lib
from rq import Queue

from app.core.config import settings

logger = logging.getLogger("finance.redis")

_redis_client: redis_lib.Redis | None = None


def get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.Redis.from_url(settings.redis_connection_url, decode_responses=True)
    return _redis_client


def get_identity_from_request(request) -> str:  # type: ignore[no-untyped-def]
    """Proxy-safe client identity using X-Forwarded-For."""
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enqueue_task(func_path: str, payload: dict) -> None:
    """Enqueue an RQ task. Raises exception with details on failure (caller should handle)."""
    queue = Queue("finance", connection=get_redis())
    queue.enqueue(func_path, payload)


def record_event(stream: str, payload: dict) -> None:
    client = get_redis()
    event = {"ts": int(time.time()), **payload}
    client.lpush(stream, str(event))
    client.ltrim(stream, 0, 999)


def is_token_blacklisted(jti: str) -> bool:
    """Return True if the given JTI has been blacklisted (i.e. logged out)."""
    try:
        client = get_redis()
        return client.exists(f"bl:jti:{jti}") == 1
    except Exception:
        # Graceful failure: do not hard-fail authenticated requests if Redis is unavailable.
        logger.warning("token_blacklist_redis_error: jti=%s", jti)
        return False


def is_rate_limited(scope: str, identity: str, limit: int, window_seconds: int) -> bool:
    """Check if a given identity is rate limited for a specific scope."""
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
        logger.warning(f"rate_limit_redis_error: scope={scope} identity={identity}")
        return False


def clear_user_financial_cache(user_id: int | str) -> None:
    """Clear all finance-related caches for a user (summary, wealth, net-worth, etc.)."""
    try:
        client = get_redis()
        # Common patterns: finance:summary:{user_id}, finance:wealth:{user_id}, finance:insights:{user_id}
        keys = client.keys(f"finance:*:{user_id}")
        if keys:
            client.delete(*keys)
            logger.info(f"Cleared {len(keys)} financial cache keys for user {user_id}")
    except Exception as e:
        logger.warning(f"cache_clear_error: user_id={user_id} error={e}")
