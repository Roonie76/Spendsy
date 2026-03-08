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
