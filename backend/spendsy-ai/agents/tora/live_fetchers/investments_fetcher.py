"""
Live investments fetcher.

Strategy: AMFI publishes every mutual-fund NAV in India as a plain-text
file at a stable public URL — no auth, no rate limiting. This is the
single most reliable live data source in the Indian financial ecosystem.

  https://www.amfiindia.com/spages/NAVAll.txt

Format: semicolon-delimited rows, one NAV per line. Updated nightly at
~11 PM IST. We don't parse every row — we extract a handful of well-known
fund codes (large-cap, mid-cap index fund NAVs) as freshness proof plus
compute category-average NAV deltas as a market-health signal.

NSE/BSE live indices are a stretch goal — their public endpoints are
rate-limited and require careful scraping. For now we rely on the cache
warmer (stage 5+) or YAML fallback for Nifty/Sensex values.

The engine's 600ms timeout means this runs quickly or not at all.
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

AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
HTTP_TIMEOUT_SECONDS = 0.5

# A handful of widely-held fund scheme codes (hardcoded — these are the
# primary trackers for Nifty50 index funds, which are what most retail
# investors compare against). Used as a freshness probe, not as a
# recommendation — SEBI disclaimer still applies.
_PROBE_SCHEME_CODES = {
    "120716": "UTI Nifty 50 Index Fund - Direct Plan - Growth",
    "119552": "HDFC Index Fund-NIFTY 50 Plan - Direct Plan",
    "120716": "Nippon India Index Fund - Nifty 50 Plan",
}


async def _fetch_amfi_text() -> str | None:
    if httpx is None:
        return None
    try:
        async with httpx.AsyncClient(
            timeout=HTTP_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Spendsy/TORA)"},
        ) as client:
            response = await client.get(AMFI_NAV_URL)
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.debug("AMFI NAV fetch failed: %s", e)
        return None


def _parse_nav_row(row: str) -> tuple[str, float, str] | None:
    """AMFI rows look like: <scheme_code>;<isin_growth>;<isin_div>;<scheme_name>;<nav>;<date>

    Some rows are headers or blank. Returns (scheme_code, nav, date) or None.
    """
    parts = row.split(";")
    if len(parts) < 6:
        return None
    code = parts[0].strip()
    if not code.isdigit():
        return None
    try:
        nav = float(parts[4].strip())
    except (ValueError, IndexError):
        return None
    date = parts[5].strip()
    return code, nav, date


def _build_live_fact(value: Any, confidence: float, date_str: str) -> dict[str, Any]:
    return {
        "value": value,
        "source": "AMFI NAVAll",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "ttl_seconds": 86400,  # daily refresh
        "confidence": confidence,
        "as_of": date_str,
    }


async def fetch_investments_live(*_args, **_kwargs) -> FetchResult:
    """Pull MF NAV snapshot from AMFI.

    Returns a compact `mf_nav_snapshot` fact with a few probe funds. The
    fallback YAML's category CAGRs, FD rates, PPF, NPS, tax_rules all remain
    authoritative — this fetcher only adds today's NAV freshness proof.
    """
    text = await _fetch_amfi_text()
    if text is None:
        return FetchResult()

    snapshot: dict[str, Any] = {}
    snapshot_date: str | None = None

    for row in text.splitlines():
        parsed = _parse_nav_row(row)
        if parsed is None:
            continue
        code, nav, date = parsed
        if code in _PROBE_SCHEME_CODES:
            snapshot[_PROBE_SCHEME_CODES[code]] = {"nav": nav, "date": date}
            snapshot_date = snapshot_date or date

    if not snapshot:
        return FetchResult()

    confidence = STRATEGY_BASE_CONFIDENCE[FetchStrategy.CACHED_DAILY]
    facts = {
        "mf_nav_snapshot": _build_live_fact(
            snapshot, confidence, snapshot_date or "unknown"
        ),
    }

    return FetchResult(
        facts=facts,
        provenance={
            "plugin_id": "investments",
            "live_source": "AMFI",
            "live_fields": ["mf_nav_snapshot"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
    )
