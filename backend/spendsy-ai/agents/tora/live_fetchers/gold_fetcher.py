"""
Live gold/silver fetcher.

Strategy: scrape IBJA (India Bullion and Jewellers Association) daily
published rates from their public page. IBJA is the authoritative body
for gold/silver spot rates in India — widely used by jewellers and
regulators.

Fallback: MCX public quotes if IBJA is unavailable.

Source URL shape (as of 2026):
  https://ibjarates.com/ — HTML page with current 22K, 24K, silver rates

The engine enforces a 600ms timeout on the whole async call. If the
scrape takes longer or HTML structure changes (breaks our selectors),
the fallback YAML wins and the user sees no lag.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

try:
    import httpx  # already a project dep
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

from ..fetch_registry import (
    STRATEGY_BASE_CONFIDENCE,
    FetchResult,
    FetchStrategy,
)

logger = logging.getLogger(__name__)

IBJA_URL = "https://ibjarates.com/"
HTTP_TIMEOUT_SECONDS = 0.5  # leave headroom under engine's 600ms per-fetch budget

# Matches "22K ... 70,800" / "24K ... 77,200" / "Silver ... 94,500" patterns in
# IBJA's HTML. Structure changes will break these — that's acceptable because
# fallback catches us.
_GOLD_22K_RE = re.compile(r"22\s*K[^\d]{0,40}([\d,]+)", re.IGNORECASE)
_GOLD_24K_RE = re.compile(r"(?:999|24\s*K|fine gold)[^\d]{0,40}([\d,]+)", re.IGNORECASE)
_SILVER_RE = re.compile(r"silver[^\d]{0,40}([\d,]+)", re.IGNORECASE)


def _parse_int(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw.replace(",", "").strip())
    except (ValueError, AttributeError):
        return None


async def _fetch_ibja_html() -> str | None:
    if httpx is None:
        return None
    try:
        async with httpx.AsyncClient(
            timeout=HTTP_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Spendsy/TORA)"},
        ) as client:
            response = await client.get(IBJA_URL)
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.debug("IBJA fetch failed: %s", e)
        return None


def _build_live_fact(value: Any, confidence: float) -> dict[str, Any]:
    return {
        "value": value,
        "source": "IBJA daily rate",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "ttl_seconds": 3600,  # 1h — gold moves slowly intraday
        "confidence": confidence,
    }


async def fetch_gold_live(*_args, **_kwargs) -> FetchResult:
    """Scrape IBJA for gold/silver spot rates.

    Returns FetchResult with only the fields it successfully parsed. The
    engine's field-level merge fills the rest from YAML fallback.
    """
    html = await _fetch_ibja_html()
    if html is None:
        return FetchResult()

    gold_22k = _parse_int(m.group(1) if (m := _GOLD_22K_RE.search(html)) else None)
    gold_24k = _parse_int(m.group(1) if (m := _GOLD_24K_RE.search(html)) else None)
    silver = _parse_int(m.group(1) if (m := _SILVER_RE.search(html)) else None)

    # Sanity range checks — IBJA values should be within plausible bounds.
    # Anything outside triggers fallback for that field.
    if gold_22k is not None and not (50000 <= gold_22k <= 200000):
        gold_22k = None
    if gold_24k is not None and not (55000 <= gold_24k <= 220000):
        gold_24k = None
    if silver is not None and not (50000 <= silver <= 300000):
        silver = None

    if not any([gold_22k, gold_24k, silver]):
        # Scrape succeeded but all selectors missed — treat as failure.
        return FetchResult()

    confidence = STRATEGY_BASE_CONFIDENCE[FetchStrategy.LIVE_API]
    spot_price_inr: dict[str, Any] = {}
    if gold_22k:
        spot_price_inr["gold_per_10g_22k"] = gold_22k
    if gold_24k:
        spot_price_inr["gold_per_10g_24k"] = gold_24k
    if silver:
        spot_price_inr["silver_per_kg"] = silver

    facts = {
        "spot_price_inr": _build_live_fact(spot_price_inr, confidence),
    }

    return FetchResult(
        facts=facts,
        provenance={
            "plugin_id": "gold",
            "live_source": "IBJA",
            "live_fields": list(spot_price_inr.keys()),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
    )
