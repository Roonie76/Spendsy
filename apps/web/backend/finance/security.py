from __future__ import annotations

from django.core.cache import cache


def client_ip(request) -> str:
    forwarded_for = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    return (request.META.get("REMOTE_ADDR") or "unknown").strip() or "unknown"


def is_rate_limited(scope: str, identity: str, limit: int, window_seconds: int) -> bool:
    key = f"rl:{scope}:{identity}"

    if cache.add(key, 1, timeout=window_seconds):
        return False

    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return False

    return count > limit
