"""Healthcare plugin: insurance, surgery, dental, IVF, gym, medicine."""

from ..fetch_registry import FetchPlugin
from ._base import build_fallback_from_yaml, stub_fetcher

PLUGIN = FetchPlugin(
    plugin_id="healthcare",
    entity_keys=[
        "health insurance", "term insurance", "80d deduction",
        "surgery", "hospital", "dental",
        "ivf", "therapy", "medicine",
    ],
    fetch_profile=[
        "insurance_premiums", "procedure_costs", "cghs_rates",
        "tax_deduction",
    ],
    token_budget=240,
    fetcher=stub_fetcher,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("healthcare"),
    priority_keys=[
        "health_insurance_annual_premium_inr",
        "term_life_insurance_annual_premium_inr_1cr_cover",
        "procedure_cost_inr", "tax_deduction_sec_80d_inr",
    ],
    critical_freshness=True,
)
