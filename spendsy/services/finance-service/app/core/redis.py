from __future__ import annotations

import logging
import time
import uuid

import redis as redis_lib
from rq import Queue

from .config import settings

logger = logging.getLogger("finance.redis")

_redis_client: redis_lib.Redis | None = None


def get_redis() -> redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.Redis.from_url(settings.redis_url, decode_responses=True)
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
    client = get_redis()
    return client.exists(f"bl:jti:{jti}") == 1
