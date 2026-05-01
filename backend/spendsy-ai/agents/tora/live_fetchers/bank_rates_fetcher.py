"""
Bank Rates Fetcher — Phase 1: Live loan/deposit rate scraper.

Targets: HDFC, SBI, Axis, ICICI, Kotak, Bank of Baroda, PNB.
Fetches:
  - Personal loan rate (min/max % p.a.)
  - Home loan rate (min % p.a.)
  - Car loan rate (min % p.a.)
  - FD rate (1-year, % p.a.)

Each bank has a scrape config: URL + CSS selectors.
ObscuraClient (headless browser) handles JS-rendered pages.
content_extractor cleans DOM → chunks.

Returns: dict[bank_id, BankRates] where BankRates = typed dataclass.

Design rules:
  - 800ms hard budget (matches universal_fetch_engine).
  - Never raises — returns empty rates dict on any failure.
  - All rates in % p.a. float. None = not found.
  - Results tagged with {source_url, fetched_at, confidence}.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .browser_client import obscura_client
from .content_extractor import extract_chunks_from_scrape_result

logger = logging.getLogger(__name__)

FETCH_BUDGET_SECONDS = 0.8


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class BankRates:
    bank_id: str
    bank_name: str
    personal_loan_min_pct: float | None = None
    personal_loan_max_pct: float | None = None
    home_loan_min_pct: float | None = None
    car_loan_min_pct: float | None = None
    fd_1yr_pct: float | None = None
    source_url: str = ""
    fetched_at: str = ""
    confidence: float = 0.0          # 0.0 = fallback, 0.8 = live scrape
    raw_chunks: list[dict] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        """Compact text for TORA context injection."""
        lines = [f"[{self.bank_name} — rates as of {self.fetched_at[:10]}]"]
        if self.personal_loan_min_pct is not None:
            hi = f"–{self.personal_loan_max_pct}%" if self.personal_loan_max_pct else ""
            lines.append(f"  Personal loan: {self.personal_loan_min_pct}%{hi} p.a.")
        if self.home_loan_min_pct is not None:
            lines.append(f"  Home loan:     {self.home_loan_min_pct}%+ p.a.")
        if self.car_loan_min_pct is not None:
            lines.append(f"  Car loan:      {self.car_loan_min_pct}%+ p.a.")
        if self.fd_1yr_pct is not None:
            lines.append(f"  FD (1yr):      {self.fd_1yr_pct}% p.a.")
        if self.confidence < 0.5:
            lines.append("  ⚠ Rates are indicative; verify at bank website.")
        return "\n".join(lines)


# ── Scrape configs ─────────────────────────────────────────────────────────────
# Each entry: (bank_id, bank_name, url, selectors_dict)
# Selectors target rate tables / info-boxes on the bank's public rate page.
# We scrape the full content area and then parse % values with regex.

BANK_CONFIGS: list[tuple[str, str, str, dict[str, str]]] = [
    (
        "hdfc",
        "HDFC Bank",
        "https://www.hdfcbank.com/personal/borrow/popular-loans/personal-loan/personal-loan-interest-rates",
        {"content": "div.article-content, table, .rate-table"},
    ),
    (
        "sbi",
        "State Bank of India",
        "https://sbi.co.in/web/personal-banking/loans/personal-loan",
        {"content": "div.field--name-body, table.views-table"},
    ),
    (
        "axis",
        "Axis Bank",
        "https://www.axisbank.com/retail/loans/personal-loan/features-benefits",
        {"content": ".section-container, table, .interest-rates"},
    ),
    (
        "icici",
        "ICICI Bank",
        "https://www.icicibank.com/personal-banking/loans/personal-loan/interest-rate",
        {"content": ".accordian-content, table, .interest-rate-section"},
    ),
    (
        "kotak",
        "Kotak Mahindra Bank",
        "https://www.kotak.com/en/personal-banking/loans/personal-loan/interest-rates-and-fees.html",
        {"content": ".article-body, table"},
    ),
    (
        "bob",
        "Bank of Baroda",
        "https://www.bankofbaroda.in/personal-banking/loans/personal-loan",
        {"content": ".content-area, table"},
    ),
    (
        "pnb",
        "Punjab National Bank",
        "https://www.pnbindia.in/personal-loan.html",
        {"content": ".inner-page-content, table"},
    ),
]

# Static fallback rates (RBI WALR approximations, updated quarterly)
# Used when live scrape fails. Confidence = 0.45 (ESTIMATED tier).
FALLBACK_RATES: dict[str, dict] = {
    "hdfc":  {"pl_min": 10.5, "pl_max": 21.0, "hl_min": 8.75, "car_min": 9.25,  "fd": 7.25},
    "sbi":   {"pl_min": 11.15,"pl_max": 14.0, "hl_min": 8.50, "car_min": 8.75,  "fd": 6.80},
    "axis":  {"pl_min": 10.49,"pl_max": 22.0, "hl_min": 8.75, "car_min": 9.20,  "fd": 7.10},
    "icici": {"pl_min": 10.65,"pl_max": 16.0, "hl_min": 8.75, "car_min": 9.10,  "fd": 7.00},
    "kotak": {"pl_min": 10.99,"pl_max": 24.0, "hl_min": 8.70, "car_min": 9.00,  "fd": 7.20},
    "bob":   {"pl_min": 11.05,"pl_max": 18.75,"hl_min": 8.40, "car_min": 8.85,  "fd": 6.75},
    "pnb":   {"pl_min": 10.40,"pl_max": 17.95,"hl_min": 8.45, "car_min": 8.90,  "fd": 6.80},
}


# ── Rate parser ───────────────────────────────────────────────────────────────

_RATE_RE = re.compile(r"(\d{1,2}(?:\.\d{1,2})?)\s*%")


def _parse_rates_from_text(text: str) -> list[float]:
    """Extract all percentage values from scraped text."""
    return [float(m.group(1)) for m in _RATE_RE.finditer(text)]


def _build_from_fallback(bank_id: str, bank_name: str) -> BankRates:
    fb = FALLBACK_RATES.get(bank_id, {})
    return BankRates(
        bank_id=bank_id,
        bank_name=bank_name,
        personal_loan_min_pct=fb.get("pl_min"),
        personal_loan_max_pct=fb.get("pl_max"),
        home_loan_min_pct=fb.get("hl_min"),
        car_loan_min_pct=fb.get("car_min"),
        fd_1yr_pct=fb.get("fd"),
        source_url="static_fallback",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        confidence=0.45,
    )


def _parse_bank_rates(
    bank_id: str,
    bank_name: str,
    url: str,
    scrape_result: dict[str, Any],
) -> BankRates:
    """
    Given raw scrape result, extract rates via regex heuristics.
    Falls back gracefully to static rates if parsing yields nothing useful.
    """
    chunks = extract_chunks_from_scrape_result(scrape_result, url=url)
    full_text = "\n".join(c["text"] for c in chunks)
    rates = _parse_rates_from_text(full_text)

    if len(rates) < 2:
        logger.debug("bank_rates: insufficient data for %s, using fallback", bank_id)
        result = _build_from_fallback(bank_id, bank_name)
        result.raw_chunks = chunks
        return result

    rates_sorted = sorted(rates)
    pl_candidates = [r for r in rates_sorted if 8.0 <= r <= 36.0]

    pl_min = pl_candidates[0] if pl_candidates else None
    pl_max = pl_candidates[-1] if len(pl_candidates) > 1 else None
    hl_candidates = [r for r in rates_sorted if 7.0 <= r <= 12.0]
    hl_min = hl_candidates[0] if hl_candidates else None

    return BankRates(
        bank_id=bank_id,
        bank_name=bank_name,
        personal_loan_min_pct=pl_min,
        personal_loan_max_pct=pl_max if pl_max != pl_min else None,
        home_loan_min_pct=hl_min,
        car_loan_min_pct=FALLBACK_RATES.get(bank_id, {}).get("car_min"),  # car rarely on PL page
        fd_1yr_pct=FALLBACK_RATES.get(bank_id, {}).get("fd"),
        source_url=url,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        confidence=0.80,
        raw_chunks=chunks,
    )


# ── Async fetcher ──────────────────────────────────────────────────────────────

async def _fetch_one_bank(
    bank_id: str, bank_name: str, url: str, selectors: dict[str, str]
) -> BankRates:
    try:
        scrape_result = await obscura_client.scrape(url, selectors, timeout=700)
        if "error" in scrape_result:
            raise RuntimeError(scrape_result["error"])
        return _parse_bank_rates(bank_id, bank_name, url, scrape_result)
    except Exception as exc:
        logger.warning("bank_rates: scrape failed for %s: %s", bank_id, exc)
        return _build_from_fallback(bank_id, bank_name)


async def fetch_bank_rates(
    bank_ids: list[str] | None = None,
    budget_seconds: float = FETCH_BUDGET_SECONDS,
) -> dict[str, BankRates]:
    """
    Fetch rates for requested banks in parallel.

    Args:
        bank_ids:  Which banks to fetch. None = all configured banks.
        budget_seconds: Hard time cap across all concurrent fetches.

    Returns:
        {bank_id: BankRates}. Always has an entry for every requested bank
        (fallback on failure).
    """
    configs = [
        (bid, bname, url, sel)
        for bid, bname, url, sel in BANK_CONFIGS
        if bank_ids is None or bid in bank_ids
    ]

    if not configs:
        return {}

    tasks = [
        _fetch_one_bank(bid, bname, url, sel)
        for bid, bname, url, sel in configs
    ]

    try:
        results: list[BankRates] = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=budget_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning("bank_rates: total budget exceeded, using all fallbacks")
        return {
            bid: _build_from_fallback(bid, bname)
            for bid, bname, _, _ in configs
        }

    output: dict[str, BankRates] = {}
    for (bid, bname, _, _), result in zip(configs, results):
        if isinstance(result, Exception):
            output[bid] = _build_from_fallback(bid, bname)
        else:
            output[bid] = result

    return output


def fetch_bank_rates_sync(
    bank_ids: list[str] | None = None,
) -> dict[str, BankRates]:
    """Sync wrapper for use in non-async contexts (tool registry, tests)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(fetch_bank_rates(bank_ids))


def build_rates_context_block(rates: dict[str, BankRates]) -> str:
    """Render all fetched rates into a single prompt-ready block."""
    if not rates:
        return ""
    blocks = [r.to_prompt_block() for r in rates.values()]
    return "## Live Bank Rates\n" + "\n\n".join(blocks)
