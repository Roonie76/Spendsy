"""
Live fetchers for plugins that have free data sources.

Each fetcher is an async function that returns a FetchResult with live
data + LIVE_API/LIVE_SCRAPE-level confidence. The engine merges this on
top of the YAML fallback — if the live fetch times out or errors, the
fallback is already computed sync and there is zero extra latency.

Phase 1 additions (Obscura web intelligence layer):
- content_extractor  — DOM → clean chunks (used by all scrapers)
- bank_rates_fetcher — live loan/FD rates from 7 major Indian banks
- car_price_fetcher  — OTR price scrape from CardDekho / CarWale

Pre-existing:
- gold (IBJA scrape)
- investments (AMFI NAV + semi-static rates)
- travel (RBI forex)
"""

from .content_extractor import extract_chunks, extract_chunks_from_scrape_result
from .bank_rates_fetcher import fetch_bank_rates, fetch_bank_rates_sync, build_rates_context_block, BankRates
from .car_price_fetcher import fetch_car_price, fetch_car_price_sync, CarPriceResult

__all__ = [
    "extract_chunks",
    "extract_chunks_from_scrape_result",
    "fetch_bank_rates",
    "fetch_bank_rates_sync",
    "build_rates_context_block",
    "BankRates",
    "fetch_car_price",
    "fetch_car_price_sync",
    "CarPriceResult",
]
