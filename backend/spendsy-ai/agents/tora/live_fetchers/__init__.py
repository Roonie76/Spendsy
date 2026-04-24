"""
Live fetchers for plugins that have free data sources.

Each fetcher is an async function that returns a FetchResult with live
data + LIVE_API/LIVE_SCRAPE-level confidence. The engine merges this on
top of the YAML fallback — if the live fetch times out or errors, the
fallback is already computed sync and there is zero extra latency.

Only 3 of 12 plugins have live fetchers at Stage 6:
- gold (IBJA scrape)
- investments (AMFI NAV + semi-static rates)
- travel (RBI forex)

The other 9 continue on CURATED_STATIC indefinitely — see PROJECT_LOG
data-strategy notes.
"""
