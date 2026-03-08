from __future__ import annotations

import json
import logging

import httpx

from ..core.config import settings
from ..core.redis import get_redis

logger = logging.getLogger("ai.finance_client")

_CACHE_TTL = 300  # 5 minutes


def fetch_finance_context(user_id: int) -> dict:
    """Fetch finance context for a given user, with 5-minute Redis cache."""
    cache_key = f"ai:finance_ctx:{user_id}"
    client = get_redis()

    # 1. Check Redis cache first
    try:
        cached = client.get(cache_key)
        if cached:
            logger.debug("finance_context cache HIT for user_id=%s", user_id)
            return json.loads(cached)
    except Exception as cache_exc:
        logger.warning("Redis cache read failed for user_id=%s: %s", user_id, str(cache_exc))

    # 2. Fetch from Finance service
    url = f"{settings.finance_service_url.rstrip('/')}/internal/finance-context/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    try:
        with httpx.Client(timeout=10.0) as http:
            response = http.get(url, headers=headers)
        response.raise_for_status()
        data: dict = response.json().get("data") or response.json()
    except Exception as exc:
        logger.error("fetch_finance_context failed for user_id=%s error=%s", user_id, str(exc))
        raise

    # 3. Store in Redis cache (best-effort; ignore write failures)
    try:
        client.setex(cache_key, _CACHE_TTL, json.dumps(data))
        logger.debug("finance_context cached for user_id=%s ttl=%ss", user_id, _CACHE_TTL)
    except Exception as cache_write_exc:
        logger.warning("Redis cache write failed for user_id=%s: %s", user_id, str(cache_write_exc))

    return data
