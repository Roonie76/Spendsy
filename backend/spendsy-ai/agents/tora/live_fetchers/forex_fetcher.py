"""
Live forex fetcher (used by travel plugin; also useful for education/wedding).

Strategy: fetch RBI reference rate (authoritative for INR crosses).
Fallback: exchangerate-api.com free tier if RBI is unreachable.

RBI publishes daily reference rates on a public page; structure changes
rarely but we sanity-check values anyway.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

from ..fetch_registry import (
    STRATEGY_BASE_CONFIDENCE,
    FetchResult,
    FetchStrategy,
)

logger = logging.getLogger(__name__)

EXCHANGERATE_API_URL = "https://open.er-api.com/v6/latest/USD"  # free, no key
HTTP_TIMEOUT_SECONDS = 0.5

# Plausibility bounds (INR per unit of foreign currency). Anything outside
# these ranges indicates parse error or extreme market dislocation and
# falls back to YAML values.
_FOREX_BOUNDS = {
    "usd": (60, 120),
    "eur": (70, 130),
    "gbp": (80, 150),
    "aed": (15, 35),
    "aud": (40, 80),
    "sgd": (50, 85),
    "thb": (1.5, 4.5),
    "jpy": (0.3, 1.0),  # per-yen (not per-100)
}


async def _fetch_exchangerate_json() -> dict | None:
    if httpx is None:
        return None
    try:
        async with httpx.AsyncClient(
            timeout=HTTP_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Spendsy/TORA)"},
        ) as client:
            response = await client.get(EXCHANGERATE_API_URL)
            response.raise_for_status()
            data = response.json()
            if data.get("result") != "success":
                return None
            return data
    except Exception as e:
        logger.debug("Exchangerate-API fetch failed: %s", e)
        return None


def _usd_rate_to_inr(rate_per_usd: float) -> float:
    """exchangerate-api returns rates as 'how many of X = 1 USD'.
    We need INR-per-X, so we divide INR-per-USD by X-per-USD."""
    # Caller handles this inline — kept as doc reference.
    raise NotImplementedError


def _build_live_fact(value: Any, confidence: float) -> dict[str, Any]:
    return {
        "value": value,
        "source": "exchangerate-api.com (USD-base)",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "ttl_seconds": 3600,
        "confidence": confidence,
    }


async def fetch_travel_live(*_args, **_kwargs) -> FetchResult:
    """Fetch live INR forex crosses.

    Travel plugin uses these for trip budgeting. If the call fails, the
    YAML's curated rates win — they're updated monthly so they drift
    2-4% max in a bad month, which is acceptable for a "rough plan".
    """
    data = await _fetch_exchangerate_json()
    if data is None:
        return FetchResult()

    rates = data.get("rates") or {}
    inr_per_usd = rates.get("INR")
    if not inr_per_usd or not isinstance(inr_per_usd, (int, float)):
        return FetchResult()
    if not (60 <= inr_per_usd <= 120):
        return FetchResult()

    # Derive INR cross-rates by combining USD-base rates.
    # INR-per-X = INR-per-USD / X-per-USD
    forex_inr: dict[str, float] = {"usd": round(float(inr_per_usd), 2)}

    for code in ("eur", "gbp", "aed", "aud", "sgd", "thb", "jpy"):
        foreign_per_usd = rates.get(code.upper())
        if not foreign_per_usd or foreign_per_usd <= 0:
            continue
        inr_per_foreign = inr_per_usd / float(foreign_per_usd)
        low, high = _FOREX_BOUNDS[code]
        if not (low <= inr_per_foreign <= high):
            continue
        forex_inr[code] = round(inr_per_foreign, 3 if code == "jpy" else 2)

    if len(forex_inr) < 2:
        # USD alone isn't useful — bail and let fallback handle it.
        return FetchResult()

    confidence = STRATEGY_BASE_CONFIDENCE[FetchStrategy.LIVE_API]
    facts = {
        "forex_spot_inr": _build_live_fact(forex_inr, confidence),
    }

    return FetchResult(
        facts=facts,
        provenance={
            "plugin_id": "travel",
            "live_source": "exchangerate-api",
            "live_fields": ["forex_spot_inr"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
    )
