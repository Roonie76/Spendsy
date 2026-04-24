"""Wedding & events plugin: wedding, reception, anniversary, birthday, events."""

from ..fetch_registry import FetchPlugin
from ._base import build_fallback_from_yaml, stub_fetcher

PLUGIN = FetchPlugin(
    plugin_id="wedding",
    entity_keys=[
        "wedding", "bridal jewellery", "wedding photographer",
        "honeymoon", "reception", "anniversary", "birthday party",
        "event",
    ],
    fetch_profile=[
        "vendor_costs", "gold_price", "forex_rates",
        "venue_index", "seasonal_pricing",
    ],
    token_budget=240,
    fetcher=stub_fetcher,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("wedding"),
    priority_keys=[
        "total_wedding_cost_inr_200_guests", "cost_breakdown_pct",
        "venue_per_plate_inr", "bridal_jewellery_inr",
        "honeymoon_budget_inr", "season",
    ],
    forex_needed=True,
)
