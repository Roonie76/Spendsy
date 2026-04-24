"""Gold & jewellery plugin: gold, silver, diamond, platinum, SGB, ETFs."""

from ..fetch_registry import FetchPlugin, FetchStrategy
from ._base import build_fallback_from_yaml
from ..live_fetchers.gold_fetcher import fetch_gold_live

PLUGIN = FetchPlugin(
    plugin_id="gold",
    entity_keys=[
        "gold", "silver", "jewellery", "diamond", "platinum", "sgb",
    ],
    fetch_profile=[
        "spot_price", "making_charges", "hallmark_norm",
        "gst_rate", "sgb_features",
    ],
    token_budget=200,
    fetcher=fetch_gold_live,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("gold"),
    strategy=FetchStrategy.LIVE_API,
    priority_keys=[
        "spot_price_inr", "making_charges_pct_range", "gst_pct",
        "sovereign_gold_bond_features", "gold_etf_features",
    ],
    sebi_disclaimer=True,
)
