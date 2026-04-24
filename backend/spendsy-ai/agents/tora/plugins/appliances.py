"""Appliances plugin: AC, fridge, washing machine, TV, geyser, microwave."""

from ..fetch_registry import FetchPlugin
from ._base import build_fallback_from_yaml, stub_fetcher

PLUGIN = FetchPlugin(
    plugin_id="appliances",
    entity_keys=[
        "ac", "fridge", "washing machine", "tv",
        "geyser", "microwave", "dishwasher", "chimney", "cooler",
    ],
    fetch_profile=[
        "live_prices", "energy_ratings", "seasonal_timing",
        "emi_offers",
    ],
    token_budget=230,
    fetcher=stub_fetcher,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("appliances"),
    priority_keys=[
        "ac_inr", "fridge_inr", "washing_machine_inr", "tv_inr",
        "seasonal_timing", "energy_star_savings_pct",
    ],
)
