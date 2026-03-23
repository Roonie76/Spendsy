from __future__ import annotations
import logging
import redis
from app.core.config import settings

logger = logging.getLogger("parser.redis")

_redis_client: redis.Redis | None = None

def get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.redis_connection_url, 
            decode_responses=True
        )
    return _redis_client
