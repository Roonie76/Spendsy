"""Travel plugin: flights, hotels, international trips, visa, insurance."""

from ..fetch_registry import FetchPlugin, FetchStrategy
from ._base import build_fallback_from_yaml
from ..live_fetchers.forex_fetcher import fetch_travel_live

PLUGIN = FetchPlugin(
    plugin_id="travel",
    entity_keys=[
        "trip", "flight", "hotel", "international",
        "europe", "usa", "dubai", "goa", "manali",
        "thailand", "singapore", "bali", "maldives", "japan trip",
        "visa", "forex",
    ],
    fetch_profile=[
        "flight_prices", "hotel_prices", "forex_rates",
        "visa_fees", "travel_insurance",
    ],
    token_budget=260,
    fetcher=fetch_travel_live,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("travel"),
    strategy=FetchStrategy.HYBRID,
    priority_keys=[
        "international_flight_rt_inr_per_person",
        "domestic_flight_rt_inr", "hotel_per_night_inr",
        "forex_spot_inr", "visa_fee_inr", "travel_insurance_inr",
    ],
    forex_needed=True,
)
