from __future__ import annotations

import json
import time

import redis

from app.core.config import settings


_redis_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(settings.redis_connection_url, decode_responses=True)
    return _redis_client


def append_message(user_id: int, role: str, content: str) -> None:
    key = f"ai:chat:{user_id}"
    payload = {"role": role, "content": content, "ts": int(time.time())}
    client = get_redis()
    client.rpush(key, json.dumps(payload))
    client.ltrim(key, -40, -1)


def load_history(user_id: int, limit: int = 20) -> list[dict]:
    key = f"ai:chat:{user_id}"
    client = get_redis()
    raw = client.lrange(key, max(0, -limit), -1)
    history: list[dict] = []
    for item in raw:
        try:
            history.append(json.loads(item))
        except Exception:
            continue
    return history


def clear_history(user_id: int) -> None:
    key = f"ai:chat:{user_id}"
    get_redis().delete(key)


def is_token_blacklisted(jti: str) -> bool:
    """Return True if the given JTI has been blacklisted (i.e. logged out)."""
    client = get_redis()
    return client.exists(f"bl:jti:{jti}") == 1
