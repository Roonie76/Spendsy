from __future__ import annotations

import time

import redis
from rq import Queue

from .config import settings


_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def enqueue_task(func_path: str, *args, **kwargs) -> None:
    queue = Queue("finance", connection=get_redis())
    queue.enqueue(func_path, *args, **kwargs)


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


def record_event(stream: str, payload: dict) -> None:
    client = get_redis()
    event = {"ts": int(time.time()), **payload}
    client.lpush(stream, str(event))
    client.ltrim(stream, 0, 999)
