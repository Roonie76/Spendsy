from __future__ import annotations

from app.core.redis import record_event


def post_parse_notification(payload: dict) -> None:
    record_event("finance:parse_notifications", payload)
