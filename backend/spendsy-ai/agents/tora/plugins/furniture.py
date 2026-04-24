"""Furniture & home improvement plugin: furniture, renovation, kitchen, bathroom."""

from ..fetch_registry import FetchPlugin
from ._base import build_fallback_from_yaml, stub_fetcher

PLUGIN = FetchPlugin(
    plugin_id="furniture",
    entity_keys=[
        "furniture", "renovation", "modular kitchen", "paint",
        "flooring", "bathroom",
    ],
    fetch_profile=[
        "product_prices", "material_costs", "contractor_rates",
    ],
    token_budget=220,
    fetcher=stub_fetcher,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("furniture"),
    priority_keys=[
        "furniture_inr", "modular_kitchen_total_inr_typical",
        "renovation_per_sqft_inr", "material_cost_inr",
        "contractor_labour_inr",
    ],
)
