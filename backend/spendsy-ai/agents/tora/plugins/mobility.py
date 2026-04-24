"""Mobility plugin: cars, bikes, EVs, commercial vehicles."""

from ..fetch_registry import FetchPlugin
from ._base import build_fallback_from_yaml, stub_fetcher

PLUGIN = FetchPlugin(
    plugin_id="mobility",
    entity_keys=[
        "car", "bike", "ev", "truck",
        "sedan", "hatchback", "suv", "scooter", "motorcycle",
    ],
    fetch_profile=[
        "prices", "bank_rates", "emi_policy", "insurance",
        "fuel_prices", "ev_subsidy",
    ],
    token_budget=250,
    fetcher=stub_fetcher,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("mobility"),
    priority_keys=[
        "car_on_road_inr", "bike_on_road_inr", "scooter_on_road_inr",
        "ev_car_on_road_inr", "auto_loan_rate_pct_pa",
        "first_year_insurance_inr", "fuel_price_inr_per_litre",
    ],
)
