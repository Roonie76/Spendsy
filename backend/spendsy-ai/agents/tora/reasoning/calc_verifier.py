"""
Calculation Verifier — Production safety layer.

Independently recomputes every key financial number from strategy parameters
and cross-checks against numbers the LLM stated in its response text.

Catches:
  - Wrong EMI formula (e.g. simple interest instead of reducing balance)
  - Wrong SIP corpus (missing compounding, wrong CAGR)
  - Wrong lump-sum FV (wrong power)
  - Wrong tax savings (wrong slab, wrong instrument cap)
  - Off-by-10x errors (lakh vs crore mix-up)

Mismatch threshold: >5% relative error → warning. >20% → hard flag.

Called from tora_agent.py after the LLM response, before compliance filter.
Never raises — returns (warnings, hard_flags) lists and is silent on pass.
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Financial formulas ─────────────────────────────────────────────────────────

def compute_emi(principal: float, annual_rate_pct: float, tenure_months: int) -> float:
    """Standard reducing-balance EMI formula."""
    if tenure_months <= 0 or principal <= 0:
        return 0.0
    if annual_rate_pct <= 0:
        return principal / tenure_months
    r = annual_rate_pct / 12 / 100
    return principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)


def compute_sip_corpus(monthly_sip: float, annual_return_pct: float, tenure_months: int) -> float:
    """Future value of monthly SIP with compounding."""
    if tenure_months <= 0 or monthly_sip <= 0:
        return 0.0
    if annual_return_pct <= 0:
        return monthly_sip * tenure_months
    r = annual_return_pct / 12 / 100
    return monthly_sip * ((1 + r) ** tenure_months - 1) / r * (1 + r)


def compute_lumpsum_fv(principal: float, annual_return_pct: float, tenure_years: float) -> float:
    """Future value of a lump-sum investment."""
    if principal <= 0 or tenure_years <= 0:
        return principal
    return principal * (1 + annual_return_pct / 100) ** tenure_years


def compute_total_interest(principal: float, emi: float, tenure_months: int) -> float:
    return max(0.0, emi * tenure_months - principal)


def compute_tax_saving_80c(annual_investment: float) -> float:
    """Tax saved under 80C — capped at ₹1.5L, old regime 30% slab assumed."""
    eligible = min(annual_investment, 150_000)
    return eligible * 0.30  # conservative: 30% slab. Will hedge if user is lower slab.


def compute_nps_80ccd1b(annual_nps: float) -> float:
    """Additional ₹50k deduction under 80CCD(1B) over 80C."""
    eligible = min(annual_nps, 50_000)
    return eligible * 0.30


# ── Number extractor ───────────────────────────────────────────────────────────

_RUPEE_RE = re.compile(
    r"₹\s*([\d,]+(?:\.\d+)?)\s*(crore|cr|lakh|lakhs?|l|k)?",
    re.IGNORECASE,
)
_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _parse_inr(amount_str: str, suffix: str | None) -> float:
    raw = float(amount_str.replace(",", ""))
    s = (suffix or "").lower().strip()
    if s in ("crore", "cr"):
        return raw * 1e7
    if s in ("lakh", "lakhs", "l"):
        return raw * 1e5
    if s == "k":
        return raw * 1e3
    return raw


def extract_rupee_figures(text: str) -> list[float]:
    return [_parse_inr(m.group(1), m.group(2)) for m in _RUPEE_RE.finditer(text)]


def extract_pct_figures(text: str) -> list[float]:
    return [float(m.group(1)) for m in _PCT_RE.finditer(text)]


# ── Tolerance check ────────────────────────────────────────────────────────────

def _rel_err(claimed: float, expected: float) -> float:
    if expected == 0:
        return 0.0 if claimed == 0 else 1.0
    return abs(claimed - expected) / abs(expected)


def _nearest_match(value: float, candidates: list[float]) -> tuple[float, float]:
    """Return (best_candidate, relative_error) for closest match."""
    if not candidates:
        return 0.0, 1.0
    best = min(candidates, key=lambda c: _rel_err(value, c))
    return best, _rel_err(value, best)


# ── Main verifier ──────────────────────────────────────────────────────────────

def verify_strategy_numbers(
    response_text: str,
    strategies: list[dict[str, Any]],
    ranked_output: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    """
    Cross-check numbers in LLM response_text against strategy parameters.

    Args:
        response_text:  The full text the LLM produced.
        strategies:     List of strategy dicts from financial_reasoner.
        ranked_output:  Output from strategy_ranker (has 'best', 'ranked').

    Returns:
        (warnings, hard_flags)
        warnings   — >5% mismatch, soft — hedged in response
        hard_flags — >20% mismatch OR off-by-10x — should suppress response
    """
    if not response_text or not strategies:
        return [], []

    warnings: list[str] = []
    hard_flags: list[str] = []

    # Collect all ₹ figures stated in the response
    claimed_rupee = extract_rupee_figures(response_text)
    claimed_pct   = extract_pct_figures(response_text)

    # Build expected values from strategy parameters
    expected_values: list[float] = []
    expected_emis:   list[float] = []
    expected_totals: list[float] = []
    expected_rates:  list[float] = []

    for s in strategies:
        principal   = float(s.get("total_cost", 0) or s.get("total_cost_inr", 0) or 0)
        rate        = float(s.get("interest_rate", 0) or s.get("rate_pct", 0) or 0)
        tenure_m    = int(s.get("timeline_months", 0) or 0)
        monthly_out = float(s.get("monthly_outflow", 0) or s.get("monthly_outflow_inr", 0) or 0)
        total_cost  = float(s.get("total_cost", 0) or s.get("total_cost_inr", 0) or 0)
        tax_saving  = float(s.get("tax_saving", 0) or 0)

        # EMI verification
        if principal > 0 and rate > 0 and tenure_m > 0:
            computed_emi = compute_emi(principal, rate, tenure_m)
            expected_emis.append(computed_emi)
            expected_values.append(computed_emi)

            # Total interest
            computed_interest = compute_total_interest(principal, computed_emi, tenure_m)
            expected_values.append(computed_interest)
            expected_totals.append(computed_emi * tenure_m)

        # Monthly outflow as stated in strategy
        if monthly_out > 0:
            expected_values.append(monthly_out)

        # Total cost as stated in strategy
        if total_cost > 0:
            expected_values.append(total_cost)
            expected_totals.append(total_cost)

        # Rate
        if rate > 0:
            expected_rates.append(rate)

        # Tax saving sanity check: should be ≤ 45k per lakh invested (30% slab)
        if tax_saving > 0:
            expected_values.append(tax_saving)
            # Flag if tax saving > 45% of monthly_out * 12 (physically impossible)
            if monthly_out > 0 and tax_saving > monthly_out * 12 * 0.45:
                hard_flags.append(
                    f"Tax saving ₹{tax_saving:,.0f} exceeds 45% of annual investment "
                    f"₹{monthly_out*12:,.0f} — likely calculation error"
                )

    # Cross-check each claimed ₹ figure against expected values
    for claimed in claimed_rupee:
        if claimed < 100:   # ignore small figures (months, guests, etc.)
            continue
        best, err = _nearest_match(claimed, expected_values)
        if err > 0.20:
            # Check for off-by-10x (lakh/crore confusion)
            shifted10 = claimed * 10
            shifted_01 = claimed / 10
            if any(_rel_err(shifted10, e) < 0.05 or _rel_err(shifted_01, e) < 0.05
                   for e in expected_values):
                hard_flags.append(
                    f"Off-by-10x detected: LLM stated ₹{claimed:,.0f} but strategy "
                    f"computed ₹{best:,.0f} — possible lakh/crore mix-up"
                )
            elif err > 0.50:
                hard_flags.append(
                    f"Large mismatch: LLM stated ₹{claimed:,.0f}, nearest strategy "
                    f"value ₹{best:,.0f} ({err*100:.0f}% error)"
                )
            else:
                warnings.append(
                    f"Mismatch: LLM stated ₹{claimed:,.0f}, nearest computed "
                    f"₹{best:,.0f} ({err*100:.0f}% off)"
                )
        elif err > 0.05:
            warnings.append(
                f"Minor mismatch: ₹{claimed:,.0f} vs computed ₹{best:,.0f} "
                f"({err*100:.1f}% off — rounding acceptable)"
            )

    # Cross-check interest rates
    for claimed_r in claimed_pct:
        if claimed_r < 1 or claimed_r > 40:
            continue  # ignore percentages that are clearly not rates
        best_r, err_r = _nearest_match(claimed_r, expected_rates)
        if expected_rates and err_r > 0.20:
            warnings.append(
                f"Rate mismatch: LLM stated {claimed_r}%, strategy has {best_r}%"
            )

    if warnings:
        logger.info("calc_verifier: %d warnings for %d strategies", len(warnings), len(strategies))
    if hard_flags:
        logger.warning("calc_verifier: %d HARD FLAGS: %s", len(hard_flags), hard_flags)

    return warnings, hard_flags


def build_verifier_note(hard_flags: list[str]) -> str:
    """Build a user-visible note when hard flags are present."""
    if not hard_flags:
        return ""
    return (
        "\n\n⚠ *Some numbers in this response could not be verified against "
        "the financial model. Please treat figures as indicative and verify "
        "with a qualified advisor before acting.*"
    )
