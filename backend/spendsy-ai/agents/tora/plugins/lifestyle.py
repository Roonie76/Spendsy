"""Lifestyle & recurring plugin: OTT, music subs, gym, dining, clubs, SaaS."""

from ..fetch_registry import FetchPlugin
from ._base import build_fallback_from_yaml, stub_fetcher

PLUGIN = FetchPlugin(
    plugin_id="lifestyle",
    entity_keys=[
        "ott", "spotify", "dining", "membership", "gym",
    ],
    fetch_profile=[
        "subscription_prices", "inflation_index",
    ],
    token_budget=180,
    fetcher=stub_fetcher,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("lifestyle"),
    priority_keys=[
        "ott_subscription_inr", "music_subscription_inr",
        "gym_membership_inr", "dining_out_inr",
        "productivity_saas_inr_monthly",
    ],
)
