from __future__ import annotations

import httpx

from ..core.config import settings


def fetch_finance_context(user_id: int) -> dict:
    url = f"{settings.finance_service_url.rstrip('/')}/internal/finance-context/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    with httpx.Client(timeout=10.0) as client:
        response = client.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data.get("data", data)
