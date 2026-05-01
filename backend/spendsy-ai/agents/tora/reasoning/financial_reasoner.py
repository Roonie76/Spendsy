"""
Financial Reasoner — Phase 3.

Given a GoalStruct + user profile, computes multiple concrete strategies.
Wraps existing tools (simulate_loan_repayment, compare_tax_regimes) into
a unified interface and generates new strategy variants.

Strategy types per goal_type:
  CAR       -> [full_cash, loan_5yr, loan_3yr, emi_with_savings]
  HOUSE     -> [full_loan, part_down_payment, max_down_payment]
  INVEST    -> [sip_equity, sip_debt, ppf, fd, hybrid]
  LOAN_REPAY-> [avalanche, snowball, partial_prepay]
  GENERIC   -> [save_and_buy, loan]

Each strategy is a dict:
  {name, description, monthly_outflow, total_cost, timeline_months,
   interest_paid, tax_saving, risk_level, feasible, notes}

Never raises. Returns [] on failure.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Optional

from .goal_decomposer import GoalStruct, GoalType

logger = logging.getLogger(__name__)

# Default rates (fallback if live bank rates not available)
DEFAULT_CAR_LOAN_RATE  = 9.25    # % p.a.
DEFAULT_HOME_LOAN_RATE = 8.75
DEFAULT_PL_RATE        = 12.0
INFLATION_RATE_PA      = 0.065   # 6.5% India avg


def _emi(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    """Standard EMI formula."""
    if annual_rate_pct <= 0:
        return principal / tenure_months
    r = annual_rate_pct / 100 / 12
    return principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)


def _total_interest(principal: float, emi: float, tenure_months: int) -> float:
    return max(0.0, emi * tenure_months - principal)


def _future_value_sip(monthly: float, annual_rate_pct: float, months: int) -> float:
    """Corpus from regular SIP."""
    r = annual_rate_pct / 100 / 12
    if r <= 0:
        return monthly * months
    return monthly * ((1 + r) ** months - 1) / r * (1 + r)


def _months_to_save(target: float, monthly_save: float, annual_rate_pct: float = 0) -> int:
    """Months to accumulate target via saving + growth."""
    if monthly_save <= 0:
        return 9999
    if annual_rate_pct <= 0:
        return math.ceil(target / monthly_save)
    r = annual_rate_pct / 100 / 12
    # FV = PMT * ((1+r)^n - 1)/r  =>  solve for n
    try:
        n = math.log(1 + target * r / monthly_save) / math.log(1 + r)
        return max(1, math.ceil(n))
    except (ValueError, ZeroDivisionError):
        return math.ceil(target / monthly_save)


# ── Strategy builders ─────────────────────────────────────────────────────────

def _car_strategies(goal: GoalStruct, surplus: float, rates: dict) -> list[dict]:
    amount = goal.target_amount or 800_000
    car_rate = rates.get("car_loan", DEFAULT_CAR_LOAN_RATE)
    strategies = []

    # 1. Full cash
    months_save = _months_to_save(amount, surplus * 0.60, annual_rate_pct=7.0)
    strategies.append({
        "name": "Save & Buy (No Loan)",
        "description": f"Save ₹{surplus*0.60:,.0f}/month, buy after {months_save}m",
        "monthly_outflow": round(surplus * 0.60),
        "total_cost": round(amount),
        "timeline_months": months_save,
        "interest_paid": 0,
        "tax_saving": 0,
        "risk_level": "low",
        "feasible": months_save <= 60,
        "notes": ["No interest cost", "Car price may rise with inflation"],
    })

    # 2. Loan 5yr
    e5 = _emi(amount, car_rate, 60)
    strategies.append({
        "name": f"Car Loan 5yr @ {car_rate}%",
        "description": f"EMI ₹{e5:,.0f}/month for 60 months",
        "monthly_outflow": round(e5),
        "total_cost": round(e5 * 60),
        "timeline_months": 60,
        "interest_paid": round(_total_interest(amount, e5, 60)),
        "tax_saving": 0,
        "risk_level": "low",
        "feasible": e5 <= surplus * 0.40,
        "notes": [
            f"EMI is {e5/surplus*100:.0f}% of surplus",
            "40% EMI rule: " + ("OK" if e5 <= surplus * 0.40 else "EXCEEDS threshold"),
        ],
    })

    # 3. Loan 3yr (lower interest, higher EMI)
    e3 = _emi(amount, car_rate, 36)
    strategies.append({
        "name": f"Car Loan 3yr @ {car_rate}%",
        "description": f"EMI ₹{e3:,.0f}/month for 36 months",
        "monthly_outflow": round(e3),
        "total_cost": round(e3 * 36),
        "timeline_months": 36,
        "interest_paid": round(_total_interest(amount, e3, 36)),
        "tax_saving": 0,
        "risk_level": "low",
        "feasible": e3 <= surplus * 0.40,
        "notes": [
            f"Saves ₹{round(_total_interest(amount, e5, 60) - _total_interest(amount, e3, 36)):,} interest vs 5yr",
        ],
    })

    # 4. 30% down, loan rest
    down = round(amount * 0.30)
    loan_amt = amount - down
    e4 = _emi(loan_amt, car_rate, 60)
    months_down = _months_to_save(down, surplus * 0.50, annual_rate_pct=6.5)
    strategies.append({
        "name": "30% Down + 5yr Loan",
        "description": f"Save ₹{down:,} down ({months_down}m), then EMI ₹{e4:,.0f}",
        "monthly_outflow": round(e4),
        "total_cost": round(down + e4 * 60),
        "timeline_months": months_down + 60,
        "interest_paid": round(_total_interest(loan_amt, e4, 60)),
        "tax_saving": 0,
        "risk_level": "low",
        "feasible": e4 <= surplus * 0.40 and months_down <= 18,
        "notes": [f"Lower EMI due to down payment", f"Down payment ready in ~{months_down}m"],
    })

    return strategies


def _house_strategies(goal: GoalStruct, surplus: float, rates: dict) -> list[dict]:
    amount = goal.target_amount or 5_000_000
    hl_rate = rates.get("home_loan", DEFAULT_HOME_LOAN_RATE)
    strategies = []

    for down_pct, label in [(0.10, "10% Down"), (0.20, "20% Down"), (0.30, "30% Down")]:
        down = round(amount * down_pct)
        loan = amount - down
        e20 = _emi(loan, hl_rate, 240)   # 20yr
        interest = _total_interest(loan, e20, 240)
        # Old regime tax benefit: principal 80C (1.5L cap) + interest 24b (2L cap)
        annual_principal_benefit = min(150_000, loan * 0.02) * 0.30  # ~30% slab
        annual_interest_benefit  = min(200_000, e20 * 12 * 0.85) * 0.30
        annual_tax_saving = round(annual_principal_benefit + annual_interest_benefit)
        months_down = _months_to_save(down, surplus * 0.60, annual_rate_pct=7.0)
        strategies.append({
            "name": f"Home Loan ({label}, 20yr @ {hl_rate}%)",
            "description": f"Down ₹{down:,} + EMI ₹{e20:,.0f}/month",
            "monthly_outflow": round(e20),
            "total_cost": round(down + e20 * 240),
            "timeline_months": months_down + 240,
            "interest_paid": round(interest),
            "tax_saving": annual_tax_saving,
            "risk_level": "medium",
            "feasible": e20 <= surplus * 0.50 and months_down <= 36,
            "notes": [
                f"Annual tax saving ~₹{annual_tax_saving:,} (old regime, 30% slab)",
                f"Down payment in ~{months_down}m at current surplus",
                "80C: principal up to ₹1.5L, 24b: interest up to ₹2L",
            ],
        })
    return strategies


def _invest_strategies(goal: GoalStruct, surplus: float, rates: dict) -> list[dict]:
    amount   = goal.target_amount or 1_000_000
    timeline = goal.timeline_months or 60
    monthly  = min(surplus * 0.50, amount / timeline)
    strategies = []

    # Equity SIP
    corpus_eq = _future_value_sip(monthly, 12.0, timeline)
    strategies.append({
        "name": "Equity SIP (12% CAGR est.)",
        "description": f"₹{monthly:,.0f}/month SIP for {timeline}m",
        "monthly_outflow": round(monthly),
        "total_cost": round(monthly * timeline),
        "timeline_months": timeline,
        "interest_paid": 0,
        "projected_corpus": round(corpus_eq),
        "goal_achievable": corpus_eq >= amount,
        "tax_saving": 0,
        "risk_level": "high",
        "feasible": monthly <= surplus * 0.50,
        "notes": [
            "LTCG >₹1L taxed at 12.5% after 1yr",
            "Returns not guaranteed — historical avg ~12%",
            "SEBI disclaimer: past returns ≠ future returns",
        ],
    })

    # Hybrid SIP
    corpus_hy = _future_value_sip(monthly, 9.0, timeline)
    strategies.append({
        "name": "Hybrid Fund SIP (9% CAGR est.)",
        "description": f"₹{monthly:,.0f}/month balanced fund",
        "monthly_outflow": round(monthly),
        "total_cost": round(monthly * timeline),
        "timeline_months": timeline,
        "interest_paid": 0,
        "projected_corpus": round(corpus_hy),
        "goal_achievable": corpus_hy >= amount,
        "tax_saving": 0,
        "risk_level": "medium",
        "feasible": monthly <= surplus * 0.50,
        "notes": ["Lower volatility than pure equity", "Good for 3-7yr goals"],
    })

    # ELSS (tax-saving)
    elss_monthly = min(monthly, 12_500)   # 1.5L / 12
    corpus_elss = _future_value_sip(elss_monthly, 12.0, max(timeline, 36))
    tax_save = round(min(150_000, elss_monthly * 12) * 0.30)
    strategies.append({
        "name": "ELSS SIP (80C tax saving)",
        "description": f"₹{elss_monthly:,.0f}/month ELSS, 3yr lock-in",
        "monthly_outflow": round(elss_monthly),
        "total_cost": round(elss_monthly * timeline),
        "timeline_months": max(timeline, 36),
        "interest_paid": 0,
        "projected_corpus": round(corpus_elss),
        "goal_achievable": corpus_elss >= amount,
        "tax_saving": tax_save,
        "risk_level": "high",
        "feasible": elss_monthly <= surplus * 0.30,
        "notes": [
            f"Annual tax saving ~₹{tax_save:,} under old regime",
            "3yr lock-in per SIP instalment",
        ],
    })

    # PPF
    ppf_monthly = min(monthly, 12_500)
    corpus_ppf = _future_value_sip(ppf_monthly, 7.1, max(timeline, 180))
    strategies.append({
        "name": "PPF (7.1% p.a., tax-free)",
        "description": f"₹{ppf_monthly:,.0f}/month PPF, 15yr lock-in",
        "monthly_outflow": round(ppf_monthly),
        "total_cost": round(ppf_monthly * 180),
        "timeline_months": 180,
        "interest_paid": 0,
        "projected_corpus": round(corpus_ppf),
        "goal_achievable": corpus_ppf >= amount,
        "tax_saving": round(min(150_000, ppf_monthly * 12) * 0.30),
        "risk_level": "low",
        "feasible": ppf_monthly <= surplus * 0.30,
        "notes": ["Sovereign guarantee", "EEE status — fully tax-free", "15yr lock-in"],
    })

    return strategies


def _loan_repay_strategies(goal: GoalStruct, surplus: float, loans: list[dict]) -> list[dict]:
    if not loans:
        return [{
            "name": "No loans detected",
            "description": "No active loans found in profile",
            "monthly_outflow": 0, "total_cost": 0, "timeline_months": 0,
            "interest_paid": 0, "tax_saving": 0, "risk_level": "low",
            "feasible": True, "notes": [],
        }]

    strategies = []
    extra = surplus * 0.30   # 30% surplus to extra payments

    # Avalanche (highest rate first)
    sorted_hi = sorted(loans, key=lambda l: l.get("interest_rate", 0), reverse=True)
    total_interest_avalanche = sum(
        _total_interest(l.get("outstanding_balance", 0), l.get("emi_amount", 0), l.get("remaining_months", 12))
        for l in sorted_hi
    )
    strategies.append({
        "name": "Avalanche Method (Highest Rate First)",
        "description": f"Extra ₹{extra:,.0f}/month to {sorted_hi[0].get('bank_name','highest-rate loan')}",
        "monthly_outflow": round(sum(l.get("emi_amount", 0) for l in loans) + extra),
        "total_cost": round(total_interest_avalanche * 0.75),
        "timeline_months": round(max(l.get("remaining_months", 12) for l in loans) * 0.80),
        "interest_paid": round(total_interest_avalanche * 0.75),
        "tax_saving": 0,
        "risk_level": "low",
        "feasible": extra > 0,
        "notes": [
            "Mathematically optimal — minimises total interest",
            f"Focus prepayments on: {sorted_hi[0].get('bank_name', 'highest-rate loan')}",
        ],
    })

    # Snowball (smallest balance first)
    sorted_lo = sorted(loans, key=lambda l: l.get("outstanding_balance", 0))
    strategies.append({
        "name": "Snowball Method (Smallest Balance First)",
        "description": f"Clear {sorted_lo[0].get('bank_name','smallest loan')} first for quick win",
        "monthly_outflow": round(sum(l.get("emi_amount", 0) for l in loans) + extra),
        "total_cost": round(total_interest_avalanche * 0.85),
        "timeline_months": round(max(l.get("remaining_months", 12) for l in loans) * 0.85),
        "interest_paid": round(total_interest_avalanche * 0.85),
        "tax_saving": 0,
        "risk_level": "low",
        "feasible": extra > 0,
        "notes": [
            "Psychologically motivating — quick wins",
            f"Start with: {sorted_lo[0].get('bank_name','smallest loan')} (₹{sorted_lo[0].get('outstanding_balance',0):,.0f})",
        ],
    })

    return strategies


# ── Main reasoner ─────────────────────────────────────────────────────────────

def compute_strategies(
    goal: GoalStruct,
    user_profile: Optional[dict[str, Any]] = None,
    live_rates: Optional[dict[str, float]] = None,
    loans: Optional[list[dict]] = None,
) -> list[dict]:
    """
    Compute multiple financial strategies for a decomposed goal.

    Args:
        goal:         GoalStruct from goal_decomposer.
        user_profile: {surplus, income, city, tier}.
        live_rates:   {car_loan, home_loan, personal_loan} % p.a. from Phase 1 fetchers.
        loans:        Active loan list from user profile (for LOAN_REPAY).

    Returns:
        List of strategy dicts, sorted by feasibility then total_cost.
    """
    profile = user_profile or {}
    surplus = float(
        profile.get("monthly_surplus") or
        profile.get("surplus") or
        profile.get("monthly_income", 0) * 0.20  # fallback: assume 20% savings rate
    )
    rates   = live_rates or {}

    try:
        if goal.goal_type == GoalType.CAR:
            strategies = _car_strategies(goal, surplus, rates)
        elif goal.goal_type == GoalType.HOUSE:
            strategies = _house_strategies(goal, surplus, rates)
        elif goal.goal_type in (GoalType.INVEST, GoalType.RETIREMENT, GoalType.EDUCATION):
            strategies = _invest_strategies(goal, surplus, rates)
        elif goal.goal_type == GoalType.LOAN_REPAY:
            strategies = _loan_repay_strategies(goal, surplus, loans or [])
        else:
            # Generic: save-and-buy vs personal loan
            amount = goal.target_amount or 100_000
            pl_rate = rates.get("personal_loan", DEFAULT_PL_RATE)
            months_save = _months_to_save(amount, surplus * 0.50)
            e_pl = _emi(amount, pl_rate, 36)
            strategies = [
                {
                    "name": "Save & Buy",
                    "description": f"Save ₹{surplus*0.50:,.0f}/month for {months_save}m",
                    "monthly_outflow": round(surplus * 0.50),
                    "total_cost": round(amount),
                    "timeline_months": months_save,
                    "interest_paid": 0,
                    "tax_saving": 0,
                    "risk_level": "low",
                    "feasible": months_save <= 24,
                    "notes": [],
                },
                {
                    "name": f"Personal Loan 3yr @ {pl_rate}%",
                    "description": f"EMI ₹{e_pl:,.0f}/month",
                    "monthly_outflow": round(e_pl),
                    "total_cost": round(e_pl * 36),
                    "timeline_months": 36,
                    "interest_paid": round(_total_interest(amount, e_pl, 36)),
                    "tax_saving": 0,
                    "risk_level": "low",
                    "feasible": e_pl <= surplus * 0.40,
                    "notes": [],
                },
            ]

        # Sort: feasible first, then by total_cost ascending
        strategies.sort(key=lambda s: (not s.get("feasible", False), s.get("total_cost", 0)))
        return strategies

    except Exception as exc:
        logger.error("financial_reasoner failed: %s", exc)
        return []
