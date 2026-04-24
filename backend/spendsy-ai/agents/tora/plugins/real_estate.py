"""Real estate plugin: buy, rent, plot, commercial."""

from ..fetch_registry import FetchPlugin
from ._base import build_fallback_from_yaml, stub_fetcher

PLUGIN = FetchPlugin(
    plugin_id="real_estate",
    entity_keys=[
        "house", "plot", "rent", "office space",
        "flat", "apartment", "villa", "bungalow", "bhk",
        "home loan", "stamp duty", "under construction",
    ],
    fetch_profile=[
        "property_prices", "home_loan_rates", "stamp_duty",
        "rental_index", "rera_status",
    ],
    token_budget=250,
    fetcher=stub_fetcher,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("real_estate"),
    priority_keys=[
        "price_per_sqft_inr", "rent_2bhk_monthly_inr",
        "home_loan_rate_pct_pa", "stamp_duty_pct_by_state",
        "max_ltv_pct",
    ],
)
