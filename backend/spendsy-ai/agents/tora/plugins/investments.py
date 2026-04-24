"""Investments plugin: stocks, MF, FD, SIP, NPS, bonds, PPF, ELSS."""

from ..fetch_registry import FetchPlugin, FetchStrategy
from ._base import build_fallback_from_yaml
from ..live_fetchers.investments_fetcher import fetch_investments_live

PLUGIN = FetchPlugin(
    plugin_id="investments",
    entity_keys=[
        "invest", "stocks", "mutual fund", "sip", "fd",
        "nps", "bonds", "ppf", "elss", "etf", "nifty", "sensex",
        "tax saving", "retirement", "income tax",
    ],
    fetch_profile=[
        "market_indices", "fd_rates", "mf_nav", "nps_returns",
        "ppf_rate", "tax_impact",
    ],
    token_budget=260,
    fetcher=fetch_investments_live,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("investments"),
    strategy=FetchStrategy.HYBRID,
    priority_keys=[
        "index_values", "fd_rate_pct_pa", "mf_category_5y_cagr_pct",
        "ppf", "nps", "tax_rules",
    ],
    sebi_disclaimer=True,
    critical_freshness=True,
)
