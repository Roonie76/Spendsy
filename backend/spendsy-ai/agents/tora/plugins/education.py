"""Education plugin: college, MBA, BTech, study abroad, coaching, certifications."""

from ..fetch_registry import FetchPlugin
from ._base import build_fallback_from_yaml, stub_fetcher

PLUGIN = FetchPlugin(
    plugin_id="education",
    entity_keys=[
        "college", "course", "mba", "btech", "masters", "phd",
        "abroad study", "coaching", "upsc", "cat", "ielts",
        "certification", "cost of living", "education loan",
    ],
    fetch_profile=[
        "tuition_fees", "forex_rates", "education_loan_rates",
        "scholarship_data", "cost_of_living",
    ],
    token_budget=240,
    fetcher=stub_fetcher,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("education"),
    priority_keys=[
        "college_annual_fee_inr", "study_abroad_total_cost_inr_per_year",
        "test_prep_fees_inr", "education_loan", "scholarships",
    ],
    forex_needed=True,
)
