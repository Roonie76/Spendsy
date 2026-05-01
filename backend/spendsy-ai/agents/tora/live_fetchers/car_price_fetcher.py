"""
Car Price Fetcher — Phase 1: Live OTR price scraper.

Sources: CarDekho (primary), CarWale (fallback).
Returns on-road price estimate for a queried car model/variant.

OTR price components fetched:
  ex_showroom   — manufacturer price
  rto           — estimated registration (7–15% of ex-showroom by state)
  insurance     — estimated first-year (2–4% of ex-showroom)
  on_road       — sum (or directly scraped if available)

Design:
  - Query-based: caller passes free-text like "Maruti Swift VXI Delhi".
  - Entity extraction: pull model + variant + city from query string.
  - Search URL built dynamically; no hardcoded model URLs.
  - 800ms total budget; fallback to city-adjusted heuristic on timeout.
  - Returns CarPriceResult dataclass. Never raises.
"""

from __future__ import annotations

import asyncio
import logging
import re
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .browser_client import obscura_client
from .content_extractor import extract_chunks_from_scrape_result

logger = logging.getLogger(__name__)

FETCH_BUDGET_SECONDS = 0.8


# ── State RTO rates (approx % of ex-showroom) ─────────────────────────────────
# Source: MoRTH guidelines. Updated ~annually.

RTO_RATES: dict[str, float] = {
    "delhi":        0.12,
    "mumbai":       0.11,
    "bangalore":    0.13,
    "bengaluru":    0.13,
    "hyderabad":    0.12,
    "chennai":      0.10,
    "kolkata":      0.105,
    "pune":         0.11,
    "ahmedabad":    0.06,
    "jaipur":       0.08,
    "lucknow":      0.08,
    "chandigarh":   0.06,
    "default":      0.10,
}

# Insurance: ~2.5% of IDV (≈ ex-showroom for first year) for petrol cars.
INSURANCE_RATE = 0.025


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class CarPriceResult:
    query: str
    model_detected: str = ""
    variant_detected: str = ""
    city_detected: str = ""
    ex_showroom_inr: float | None = None
    rto_inr: float | None = None
    insurance_inr: float | None = None
    on_road_inr: float | None = None
    source_url: str = ""
    fetched_at: str = ""
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)
    raw_chunks: list[dict] = field(default_factory=list)

    def compute_on_road(self, city: str = "") -> None:
        """Derive on_road from components if not directly scraped."""
        if self.on_road_inr is not None:
            return
        if self.ex_showroom_inr is None:
            return
        city_key = city.lower().strip() or self.city_detected.lower()
        rto_rate = RTO_RATES.get(city_key, RTO_RATES["default"])
        self.rto_inr = self.rto_inr or round(self.ex_showroom_inr * rto_rate)
        self.insurance_inr = self.insurance_inr or round(self.ex_showroom_inr * INSURANCE_RATE)
        self.on_road_inr = self.ex_showroom_inr + self.rto_inr + self.insurance_inr

    def to_prompt_block(self) -> str:
        model_label = self.model_detected or self.query
        lines = [f"[Car Price — {model_label} ({self.fetched_at[:10]})]"]
        if self.ex_showroom_inr:
            lines.append(f"  Ex-showroom:  ₹{self.ex_showroom_inr:,.0f}")
        if self.rto_inr:
            lines.append(f"  RTO/tax:      ₹{self.rto_inr:,.0f}")
        if self.insurance_inr:
            lines.append(f"  Insurance:    ₹{self.insurance_inr:,.0f}")
        if self.on_road_inr:
            lines.append(f"  On-road est:  ₹{self.on_road_inr:,.0f}")
        for note in self.notes:
            lines.append(f"  ℹ {note}")
        if self.confidence < 0.5:
            lines.append("  ⚠ Prices indicative. Verify at dealer / CarDekho.")
        return "\n".join(lines)


# ── Entity extractor ───────────────────────────────────────────────────────────

_CITY_KEYWORDS = list(RTO_RATES.keys()) + [
    "noida", "gurugram", "gurgaon", "faridabad", "bhopal",
    "indore", "nagpur", "surat", "vadodara", "kochi", "coimbatore",
]

def _extract_entities(query: str) -> tuple[str, str, str]:
    """
    Returns (model_hint, variant_hint, city).
    Heuristic: city is the first known city word; variant is trim-level
    (last all-caps / known trim word); model is whatever remains.
    """
    q_lower = query.lower()
    city = ""
    for c in _CITY_KEYWORDS:
        if c in q_lower:
            city = c
            break

    # Strip city from query for model/variant parsing
    model_str = re.sub(re.escape(city), "", query, flags=re.IGNORECASE).strip()
    # Trim-level heuristics: last word that's all-caps or known suffix
    trim_re = re.compile(
        r"\b(ZXI|VXI|LXI|ZDI|VDI|LDI|ZST|VCI|AMT|CVT|DCT|"
        r"S|SE|SX|EX|LX|ZX|GT|GTS|RS|TOP|PLUS|TURBO|ELECTRIC|EV|HYBRID)\b",
        re.IGNORECASE,
    )
    variant_match = trim_re.search(model_str)
    variant = variant_match.group(0) if variant_match else ""
    model = trim_re.sub("", model_str).strip()

    return model.strip(), variant.strip(), city.strip()


# ── Price parser ───────────────────────────────────────────────────────────────

_PRICE_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([0-9,]+(?:\.[0-9]+)?)\s*(?:lakh|lac|L|lacs)?",
    re.IGNORECASE,
)
_LAKH_RE = re.compile(r"\b([0-9]+(?:\.[0-9]+)?)\s*(?:lakh|lac|L|lacs)\b", re.IGNORECASE)


def _parse_inr(text: str) -> float | None:
    """Extract the first ₹ value from text. Handles lakh notation."""
    # Try ₹ prefix
    m = _PRICE_RE.search(text)
    if m:
        raw = float(m.group(1).replace(",", ""))
        # Detect if value is in lakhs (< 100 likely = lakh figure)
        if raw < 200:
            return raw * 100_000
        return raw

    # Try bare lakh
    m2 = _LAKH_RE.search(text)
    if m2:
        return float(m2.group(1)) * 100_000

    return None


def _extract_prices_from_chunks(chunks: list[dict]) -> dict[str, float | None]:
    """Scan all chunks for ex-showroom and on-road prices."""
    ex_showroom = None
    on_road = None

    for chunk in chunks:
        text = chunk.get("text", "")
        if ex_showroom is None and re.search(r"ex.?showroom", text, re.IGNORECASE):
            ex_showroom = _parse_inr(text)
        if on_road is None and re.search(r"on.?road", text, re.IGNORECASE):
            on_road = _parse_inr(text)
        if ex_showroom and on_road:
            break

    return {"ex_showroom": ex_showroom, "on_road": on_road}


# ── Scrapers ───────────────────────────────────────────────────────────────────

def _build_cardekho_url(model: str, city: str) -> str:
    slug = re.sub(r"\s+", "-", model.lower().strip())
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    city_slug = city.lower().strip() or "india"
    return f"https://www.cardekho.com/cars/{slug}/on-road-price-in-{city_slug}.htm"


def _build_carwale_url(model: str) -> str:
    slug = re.sub(r"\s+", "-", model.lower().strip())
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    return f"https://www.carwale.com/new/{slug}/pricelist/"


async def _scrape_cardekho(model: str, city: str) -> tuple[dict[str, Any], str]:
    url = _build_cardekho_url(model, city)
    selectors = {
        "price_section": ".price-block, .on-road-price, .priceBreakup",
        "ex_showroom":   ".ex-showroom, td:contains('Ex-Showroom')",
    }
    result = await obscura_client.scrape(url, selectors, timeout=700)
    return result, url


async def _scrape_carwale(model: str) -> tuple[dict[str, Any], str]:
    url = _build_carwale_url(model)
    selectors = {
        "price_table": ".price-table, .o-bdLst, .price-block",
    }
    result = await obscura_client.scrape(url, selectors, timeout=700)
    return result, url


# ── Main async fetcher ─────────────────────────────────────────────────────────

async def fetch_car_price(query: str) -> CarPriceResult:
    """
    Fetch OTR price for a car described in natural-language `query`.

    Args:
        query: e.g. "Maruti Swift VXI Delhi" or "Tata Nexon EV Max Pune"

    Returns:
        CarPriceResult — always populated (fallback heuristics if scrape fails).
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    model, variant, city = _extract_entities(query)

    result = CarPriceResult(
        query=query,
        model_detected=model,
        variant_detected=variant,
        city_detected=city,
        fetched_at=fetched_at,
    )

    if not model:
        result.notes.append("Could not identify car model from query.")
        result.confidence = 0.0
        return result

    # Try CardDekho first, CarWale as fallback
    scrape_result: dict[str, Any] = {}
    source_url = ""

    try:
        scrape_result, source_url = await asyncio.wait_for(
            _scrape_cardekho(model, city),
            timeout=FETCH_BUDGET_SECONDS,
        )
        if "error" in scrape_result:
            raise RuntimeError(scrape_result["error"])
    except Exception as exc:
        logger.debug("car_price: CardDekho failed (%s), trying CarWale", exc)
        try:
            scrape_result, source_url = await asyncio.wait_for(
                _scrape_carwale(model),
                timeout=FETCH_BUDGET_SECONDS * 0.6,
            )
        except Exception as exc2:
            logger.warning("car_price: both scrapers failed: %s", exc2)
            scrape_result = {}
            source_url = ""

    chunks = extract_chunks_from_scrape_result(scrape_result, url=source_url)
    prices = _extract_prices_from_chunks(chunks)

    result.source_url = source_url
    result.raw_chunks = chunks
    result.ex_showroom_inr = prices.get("ex_showroom")
    result.on_road_inr = prices.get("on_road")

    if result.ex_showroom_inr or result.on_road_inr:
        result.confidence = 0.80
        result.compute_on_road(city)
        result.notes.append(f"Source: {source_url}")
    else:
        # Pure heuristic fallback — generic segment estimates
        result.confidence = 0.30
        result.notes.append("Live price unavailable. Estimate based on segment.")
        result.notes.append("Verify at cardekho.com or carwale.com.")
        _apply_segment_estimate(result, model)

    return result


def _apply_segment_estimate(result: CarPriceResult, model: str) -> None:
    """Rough segment-based ex-showroom estimate when scraping fails."""
    m = model.lower()
    if any(k in m for k in ["nexon", "venue", "sonet", "kiger", "magnite"]):
        result.ex_showroom_inr = 900_000   # compact SUV base
    elif any(k in m for k in ["swift", "baleno", "altroz", "i20", "jazz"]):
        result.ex_showroom_inr = 650_000   # premium hatchback base
    elif any(k in m for k in ["city", "verna", "dzire", "amaze"]):
        result.ex_showroom_inr = 900_000   # sedan base
    elif any(k in m for k in ["creta", "seltos", "kicks"]):
        result.ex_showroom_inr = 1_100_000  # mid SUV base
    elif any(k in m for k in ["fortuner", "endeavour", "pajero"]):
        result.ex_showroom_inr = 3_200_000  # full-size SUV
    else:
        result.ex_showroom_inr = 800_000   # generic mid-segment
    result.compute_on_road()


def fetch_car_price_sync(query: str) -> CarPriceResult:
    """Sync wrapper for tool registry / non-async contexts."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(fetch_car_price(query))
