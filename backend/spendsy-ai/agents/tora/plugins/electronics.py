"""Electronics plugin: laptops, phones, tablets, cameras, monitors."""

from ..fetch_registry import FetchPlugin
from ._base import build_fallback_from_yaml, stub_fetcher

PLUGIN = FetchPlugin(
    plugin_id="electronics",
    entity_keys=[
        "laptop", "phone", "tablet", "camera",
        "smartwatch", "pc", "monitor", "electronics sale",
    ],
    fetch_profile=[
        "live_prices", "price_history", "emi_offers",
        "upcoming_sales",
    ],
    token_budget=220,
    fetcher=stub_fetcher,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("electronics"),
    priority_keys=[
        "laptop_inr", "phone_inr", "tablet_inr", "smartwatch_inr",
        "sale_windows", "emi_options",
    ],
)
