"""Mobility plugin: cars, bikes, EVs, commercial vehicles.

Phase 1 upgrade: real live fetcher wiring car_price_fetcher + bank_rates_fetcher.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from ..fetch_registry import FetchPlugin, FetchResult, FetchStrategy, fact
from ..live_fetchers.car_price_fetcher import fetch_car_price
from ..live_fetchers.bank_rates_fetcher import fetch_bank_rates
from ._base import build_fallback_from_yaml

logger = logging.getLogger(__name__)


async def _mobility_fetcher(
    entity: str = "",
    surplus: Optional[float] = None,
    city: Optional[str] = None,
    **_kwargs,
) -> FetchResult:
    """Live fetcher: concurrent OTR price + auto loan rates."""
    now = datetime.now(timezone.utc).isoformat()
    query = f"{entity} {city or ''}".strip()

    car_task = asyncio.create_task(fetch_car_price(query))
    rates_task = asyncio.create_task(
        fetch_bank_rates(bank_ids=["hdfc", "sbi", "axis", "icici"])
    )

    car_result = await car_task
    rates = await rates_task

    facts: dict = {}
    options: list = []
    constraints: list = []

    if car_result.on_road_inr:
        facts["car_on_road_inr"] = fact(
            value=car_result.on_road_inr,
            source=car_result.source_url or "cardekho",
            fetched_at=car_result.fetched_at,
            ttl_seconds=86400,
            confidence=car_result.confidence,
        )
    if car_result.ex_showroom_inr:
        facts["car_ex_showroom_inr"] = fact(
            value=car_result.ex_showroom_inr,
            source=car_result.source_url or "cardekho",
            fetched_at=now,
            ttl_seconds=86400,
            confidence=car_result.confidence,
        )
    if car_result.rto_inr:
        facts["car_rto_inr"] = fact(
            value=car_result.rto_inr,
            source="rto_estimate",
            fetched_at=now,
            ttl_seconds=86400,
            confidence=0.70,
        )
    if car_result.insurance_inr:
        facts["first_year_insurance_inr"] = fact(
            value=car_result.insurance_inr,
            source="insurance_estimate",
            fetched_at=now,
            ttl_seconds=86400,
            confidence=0.65,
        )

    car_loan_rates = [
        r.car_loan_min_pct for r in rates.values()
        if r.car_loan_min_pct is not None
    ]
    if car_loan_rates:
        best_rate = min(car_loan_rates)
        facts["auto_loan_rate_pct_pa"] = fact(
            value=best_rate,
            source="live_bank_scrape",
            fetched_at=now,
            ttl_seconds=3600,
            confidence=0.80,
        )
        on_road = car_result.on_road_inr
        if on_road and surplus:
            for bank_id, rate_obj in rates.items():
                if rate_obj.car_loan_min_pct is None:
                    continue
                r = rate_obj.car_loan_min_pct / 100 / 12
                n = 60
                if r > 0:
                    emi = round(on_road * r * (1 + r) ** n / ((1 + r) ** n - 1))
                else:
                    emi = round(on_road / n)
                options.append({
                    "bank": rate_obj.bank_name,
                    "rate_pct_pa": rate_obj.car_loan_min_pct,
                    "loan_amount_inr": on_road,
                    "tenure_months": n,
                    "emi_inr": emi,
                    "affordable": emi <= (surplus * 0.40),
                })
            options.sort(key=lambda o: o["rate_pct_pa"])

    constraints.append("EMI should not exceed 40% of monthly surplus.")
    constraints.append("Include insurance renewal cost in year 2+ budgeting.")
    if "ev" in (entity or "").lower():
        constraints.append(
            "Check FAME II / state EV subsidy eligibility before quoting final price."
        )

    provenance = {
        "plugin_id": "mobility",
        "strategy": FetchStrategy.LIVE_SCRAPE.value,
        "car_confidence": car_result.confidence,
        "rates_banks": list(rates.keys()),
        "any_fallback_used": car_result.confidence < 0.5,
    }

    return FetchResult(
        facts=facts,
        options=options,
        constraints=constraints,
        provenance=provenance,
    )


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
    fetcher=_mobility_fetcher,
    fallback=lambda *_a, **_k: build_fallback_from_yaml("mobility"),
    strategy=FetchStrategy.LIVE_SCRAPE,
    priority_keys=[
        "car_on_road_inr", "car_ex_showroom_inr", "car_rto_inr",
        "first_year_insurance_inr", "auto_loan_rate_pct_pa",
    ],
)
