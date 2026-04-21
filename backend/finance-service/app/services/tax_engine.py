"""
Tax Computation Engine — Server-side source of truth for Indian Income Tax calculations.

Covers:
  - Old Regime (FY 2025-26): ₹2.5L / ₹5L / ₹10L slabs, 87A rebate ≤ ₹5L
  - New Regime (FY 2025-26 Budget): ₹4L / ₹8L / ₹12L / ₹16L / ₹20L / ₹24L, rebate ≤ ₹12L
  - Surcharge tiers with marginal relief
  - 4% Health & Education Cess
  - Capital Gains: STCG 111A (20%), LTCG 112A (12.5%), Crypto 115BBH (30%)
  - Chapter VI-A deductions with statutory limits
  - House Property: 30% standard deduction on NAV, ₹2L loss cap
  - Presumptive taxation 44AD / 44ADA
  - ITR form selection logic (ITR-1 through ITR-7)
  - Advance tax schedule computation
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


# ─── Tax Constants (FY 2025-26) ────────────────────────────────────────────────

NEW_REGIME_SLABS = [
    (400_000, 0.00),
    (800_000, 0.05),
    (1_200_000, 0.10),
    (1_600_000, 0.15),
    (2_000_000, 0.20),
    (2_400_000, 0.25),
    (float("inf"), 0.30),
]

OLD_REGIME_SLABS = [
    (250_000, 0.00),
    (500_000, 0.05),
    (1_000_000, 0.20),
    (float("inf"), 0.30),
]

OLD_REGIME_SLABS_SENIOR = [
    (300_000, 0.00),
    (500_000, 0.05),
    (1_000_000, 0.20),
    (float("inf"), 0.30),
]

OLD_REGIME_SLABS_SUPER_SENIOR = [
    (500_000, 0.00),
    (1_000_000, 0.20),
    (float("inf"), 0.30),
]

SURCHARGE_BRACKETS = [
    (5_000_000, 0.10),
    (10_000_000, 0.15),
    (20_000_000, 0.25),
    (50_000_000, 0.37),
]

CESS_RATE = 0.04

DEDUCTION_LIMITS = {
    "section_80c": 150_000,
    "section_80ccd_1b": 50_000,
    "section_80d_self": 25_000,
    "section_80d_self_senior": 50_000,
    "section_80d_parents": 25_000,
    "section_80d_parents_senior": 50_000,
    "section_80tta": 10_000,
    "section_80ttb_senior": 50_000,
    "section_80ee": 50_000,
    "section_80eeb": 150_000,
    "section_80gg_monthly": 5_000,
    "section_80u": 75_000,
    "section_80u_severe": 125_000,
    "section_24b_sop": 200_000,
}

CG_RATES = {
    "stcg_111a": 0.20,      # Listed equity STCG
    "ltcg_112a": 0.125,     # Listed equity LTCG
    "ltcg_112a_exempt": 125_000,
    "ltcg_112": 0.125,      # Other assets LTCG (no indexation post Budget 2024)
    "crypto_vda": 0.30,     # Section 115BBH
}


# ─── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class TaxInput:
    """All user inputs needed for tax computation."""
    # Income heads
    salary: float = 0
    house_property: float = 0
    business_income: float = 0
    capital_gains: float = 0
    other_income: float = 0
    interest_income: float = 0
    agricultural_income: float = 0

    # Salary components (optional granular breakup)
    salary_components: dict[str, float] = field(default_factory=dict)

    # House property details
    properties: list[dict[str, Any]] = field(default_factory=list)

    # Capital gains detail
    capital_gains_detail: dict[str, float] = field(default_factory=dict)

    # Deductions
    section_80c: float = 0
    nps_80ccd: float = 0
    employer_nps: float = 0
    section_80d: float = 0
    section_80d_parents: float = 0
    section_80e: float = 0
    section_80ee: float = 0
    section_80eeb: float = 0
    section_80g: float = 0
    section_80gg: float = 0
    section_80tta: float = 0
    section_80u: float = 0
    home_loan_interest: float = 0
    hra: float = 0

    # Profile
    age: int = 30
    is_presumptive: bool = False
    is_metro: bool = False
    parents_are_senior: bool = False
    is_nri: bool = False
    has_foreign_assets: bool = False
    is_director: bool = False
    has_unlisted_equity: bool = False
    entity_type: str = "individual"

    # Filing
    advance_tax_paid: float = 0
    tds_deducted: float = 0


@dataclass
class TaxBreakdown:
    """Detailed output of tax computation."""
    regime: str
    gross_salary: float
    gross_total_income: float
    total_deductions: float
    taxable_income: float
    base_tax: float
    surcharge: float
    surcharge_rate: float
    cess: float
    capital_gains_tax: float
    total_tax: float
    effective_rate: float
    rebate_applied: float


@dataclass
class RegimeComparison:
    """Side-by-side comparison result."""
    old_regime: TaxBreakdown
    new_regime: TaxBreakdown
    recommended_regime: str
    savings: float
    breakeven_deductions: float
    itr_form: dict[str, str]
    audit_errors: list[dict]
    audit_warnings: list[dict]
    advance_tax_schedule: list[dict]
    recommendations: list[dict]


# ─── Core Computation ──────────────────────────────────────────────────────────

def _slab_tax(income: float, slabs: list[tuple[float, float]]) -> float:
    """Compute tax from slab schedule."""
    tax = 0.0
    prev = 0.0
    for limit, rate in slabs:
        if income > prev:
            taxable_in_slab = min(income - prev, limit - prev)
            tax += taxable_in_slab * rate
        prev = limit
        if income <= limit:
            break
    return tax


def _compute_surcharge(
    base_tax: float,
    income: float,
    max_rate: float,
    slabs: list[tuple[float, float]],
) -> tuple[float, float]:
    """Compute surcharge with marginal relief. Returns (surcharge, rate)."""
    applicable_rate = 0.0
    for threshold, rate in SURCHARGE_BRACKETS:
        if income > threshold and rate <= max_rate:
            applicable_rate = rate

    if applicable_rate == 0:
        return 0.0, 0.0

    raw_surcharge = base_tax * applicable_rate

    # Marginal relief: total (tax + surcharge) should not exceed
    # (tax at threshold) + (income exceeding threshold)
    applicable_threshold = None
    for threshold, rate in SURCHARGE_BRACKETS:
        if income > threshold and rate <= max_rate:
            applicable_threshold = threshold

    if applicable_threshold:
        tax_at_threshold = _slab_tax(applicable_threshold, slabs)
        marginal_excess = income - applicable_threshold
        total_with_surcharge = base_tax + raw_surcharge
        if total_with_surcharge - tax_at_threshold > marginal_excess:
            effective_surcharge = max(0.0, tax_at_threshold + marginal_excess - base_tax)
            return effective_surcharge, applicable_rate

    return raw_surcharge, applicable_rate


def _compute_house_property_income(properties: list[dict], hp_value: float) -> float:
    """Compute net income from house property."""
    if not properties:
        return hp_value

    total = 0.0
    for prop in properties:
        prop_type = prop.get("property_type", "self_occupied")
        if prop_type == "self_occupied":
            interest = min(float(prop.get("loan_interest", 0)), 200_000)
            total -= interest
        else:
            rent = float(prop.get("annual_rent", 0))
            municipal = float(prop.get("municipal_tax", 0))
            nav = rent - municipal
            std_ded = nav * 0.30  # 30% standard deduction on NAV
            interest = float(prop.get("loan_interest", 0))
            total += nav - std_ded - interest

    # Loss from house property capped at ₹2L for set-off
    return max(total, -200_000)


def _compute_capital_gains_tax(detail: dict[str, float]) -> float:
    """Compute capital gains tax at special rates (computed separately from slab tax)."""
    cg_tax = 0.0

    # STCG 111A: Listed equity + equity MFs
    stcg_111a = float(detail.get("listed_equity_stcg", 0)) + float(detail.get("equity_mf_stcg", 0))
    if stcg_111a > 0:
        cg_tax += stcg_111a * CG_RATES["stcg_111a"]

    # LTCG 112A: Listed equity + equity MFs (exempt up to ₹1.25L)
    ltcg_112a = float(detail.get("listed_equity_ltcg", 0)) + float(detail.get("equity_mf_ltcg", 0))
    if ltcg_112a > CG_RATES["ltcg_112a_exempt"]:
        cg_tax += (ltcg_112a - CG_RATES["ltcg_112a_exempt"]) * CG_RATES["ltcg_112a"]

    # Crypto / VDA (Section 115BBH — flat 30%, no set-off)
    crypto = float(detail.get("crypto_vda", 0))
    if crypto > 0:
        cg_tax += crypto * CG_RATES["crypto_vda"]

    # Non-equity LTCG at 12.5%
    non_eq_ltcg = sum(
        float(detail.get(k, 0))
        for k in ("debt_mf_ltcg", "property_ltcg", "gold_ltcg", "unlisted_ltcg")
    )
    if non_eq_ltcg > 0:
        cg_tax += non_eq_ltcg * CG_RATES["ltcg_112"]

    # Apply 4% cess on CG tax
    cg_cess = cg_tax * CESS_RATE
    return cg_tax + cg_cess


def compute_tax(tax_input: TaxInput, regime: str = "new") -> TaxBreakdown:
    """
    Compute full tax liability under the specified regime.

    Parameters
    ----------
    tax_input : TaxInput
        All user-provided income, deduction, and profile data.
    regime : str
        Either "new" or "old".

    Returns
    -------
    TaxBreakdown
        Detailed computation result.
    """
    # 1. Gross salary
    gross_salary = tax_input.salary
    if tax_input.salary_components:
        from_components = sum(
            v for k, v in tax_input.salary_components.items()
            if k not in ("epf_employer", "nps_employer", "professional_tax", "gratuity", "leave_encashment")
        )
        if from_components > 0:
            gross_salary = from_components

    # 2. House property income
    hp_income = _compute_house_property_income(
        tax_input.properties, tax_input.house_property
    )

    # 3. Business income (with presumptive if applicable)
    business = tax_input.business_income
    if tax_input.is_presumptive and business <= 30_000_000:
        business = business * 0.5  # 44ADA deemed profit

    # 4. Gross total income (excl capital gains — taxed separately)
    gti = gross_salary + hp_income + business + tax_input.other_income + tax_input.interest_income

    # 5. Standard deduction
    std_ded = 75_000 if regime == "new" else 50_000
    if gross_salary <= 0:
        std_ded = 0

    # 6. Chapter VI-A deductions
    total_deductions = std_ded
    if regime == "old":
        limits = DEDUCTION_LIMITS

        total_deductions += min(tax_input.section_80c, limits["section_80c"])
        total_deductions += min(tax_input.nps_80ccd, limits["section_80ccd_1b"])

        # 80D: age-aware limits
        d_self_limit = limits["section_80d_self_senior"] if tax_input.age >= 60 else limits["section_80d_self"]
        d_parent_limit = limits["section_80d_parents_senior"] if tax_input.parents_are_senior else limits["section_80d_parents"]
        total_deductions += min(tax_input.section_80d, d_self_limit)
        total_deductions += min(tax_input.section_80d_parents, d_parent_limit)

        total_deductions += tax_input.section_80e  # No limit
        total_deductions += min(tax_input.section_80ee, limits["section_80ee"])
        total_deductions += min(tax_input.section_80eeb, limits["section_80eeb"])
        total_deductions += tax_input.section_80g  # Varies (50% or 100%)
        total_deductions += min(tax_input.section_80gg, limits["section_80gg_monthly"] * 12)

        tta_limit = limits["section_80ttb_senior"] if tax_input.age >= 60 else limits["section_80tta"]
        total_deductions += min(tax_input.section_80tta, tta_limit)
        total_deductions += min(tax_input.section_80u, limits["section_80u"])
        total_deductions += min(tax_input.home_loan_interest, limits["section_24b_sop"])
        total_deductions += tax_input.hra

    # Employer NPS (80CCD(2)) — allowed in BOTH regimes
    total_deductions += tax_input.employer_nps

    # 7. Taxable income
    taxable_income = max(0.0, gti - total_deductions)

    # 8. Pick slabs
    if regime == "new":
        slabs = NEW_REGIME_SLABS
        max_surcharge_rate = 0.25
        rebate_limit = 1_200_000
        rebate_max = 60_000
    else:
        age_cat = "super_senior" if tax_input.age >= 80 else ("senior" if tax_input.age >= 60 else "general")
        if age_cat == "super_senior":
            slabs = OLD_REGIME_SLABS_SUPER_SENIOR
        elif age_cat == "senior":
            slabs = OLD_REGIME_SLABS_SENIOR
        else:
            slabs = OLD_REGIME_SLABS
        max_surcharge_rate = 0.37
        rebate_limit = 500_000
        rebate_max = 12_500

    # 9. Base tax from slabs
    base_tax = _slab_tax(taxable_income, slabs)

    # 10. Rebate u/s 87A
    rebate_applied = 0.0
    if regime == "new":
        if taxable_income <= rebate_limit:
            rebate_applied = base_tax
            base_tax = 0.0
        elif taxable_income <= rebate_limit + rebate_max:
            marginal = taxable_income - rebate_limit
            original = base_tax
            base_tax = min(base_tax, marginal)
            rebate_applied = original - base_tax
    else:
        if taxable_income <= rebate_limit:
            rebate_applied = min(base_tax, rebate_max)
            base_tax = max(0.0, base_tax - rebate_applied)

    # 11. Surcharge with marginal relief
    surcharge, surcharge_rate = _compute_surcharge(base_tax, taxable_income, max_surcharge_rate, slabs)

    # 12. Cess
    cess = (base_tax + surcharge) * CESS_RATE

    # 13. Capital gains tax
    cg_tax = _compute_capital_gains_tax(tax_input.capital_gains_detail)

    # 14. Total
    total_tax = base_tax + surcharge + cess + cg_tax

    effective_rate = (total_tax / gti * 100) if gti > 0 else 0.0

    return TaxBreakdown(
        regime=regime,
        gross_salary=gross_salary,
        gross_total_income=gti + tax_input.capital_gains,
        total_deductions=total_deductions,
        taxable_income=taxable_income,
        base_tax=base_tax,
        surcharge=surcharge,
        surcharge_rate=surcharge_rate,
        cess=cess,
        capital_gains_tax=cg_tax,
        total_tax=total_tax,
        effective_rate=round(effective_rate, 2),
        rebate_applied=rebate_applied,
    )


# ─── Regime Comparison ─────────────────────────────────────────────────────────

def compare_regimes(tax_input: TaxInput) -> RegimeComparison:
    """Compute tax under both regimes and return a full comparison."""
    old = compute_tax(tax_input, "old")
    new = compute_tax(tax_input, "new")

    recommended = "new" if new.total_tax <= old.total_tax else "old"
    savings = abs(old.total_tax - new.total_tax)

    # Breakeven: how many more deductions in old regime to beat new regime
    breakeven = 0.0
    if recommended == "new" and old.taxable_income > 0:
        # Rough estimate: deductions * marginal rate ≈ savings
        marginal_rate = 0.30  # Assume 30% bracket
        breakeven = savings / marginal_rate if marginal_rate > 0 else 0

    itr_form = determine_itr_form(tax_input)
    errors, warnings = run_audit_checks(tax_input)
    schedule = compute_advance_tax_schedule(max(old.total_tax, new.total_tax))
    tips = generate_recommendations(tax_input, old, new)

    return RegimeComparison(
        old_regime=old,
        new_regime=new,
        recommended_regime=recommended,
        savings=savings,
        breakeven_deductions=breakeven,
        itr_form=itr_form,
        audit_errors=errors,
        audit_warnings=warnings,
        advance_tax_schedule=schedule,
        recommendations=tips,
    )


# ─── ITR Form Selection ───────────────────────────────────────────────────────

def determine_itr_form(tax_input: TaxInput) -> dict[str, str]:
    """Choose the correct ITR form based on income profile."""
    salary = tax_input.salary
    business = tax_input.business_income
    cg = tax_input.capital_gains
    cg_detail = tax_input.capital_gains_detail
    other = tax_input.other_income + tax_input.interest_income
    total = salary + abs(tax_input.house_property) + business + cg + other

    entity = tax_input.entity_type
    if entity == "company":
        return {"form": "ITR-6", "name": "Company", "reason": "Companies must file ITR-6"}
    if entity == "trust":
        return {"form": "ITR-7", "name": "Trust/Institution", "reason": "Trusts file ITR-7"}
    if entity in ("firm", "llp"):
        return {"form": "ITR-5", "name": "Firm/LLP", "reason": "Firms and LLPs file ITR-5"}

    has_business = business > 0
    has_cg = cg > 0 or any(float(v) > 0 for v in cg_detail.values())
    has_crypto = float(cg_detail.get("crypto_vda", 0)) > 0

    if has_business:
        if tax_input.is_presumptive and total <= 5_000_000 and not has_cg and not tax_input.has_foreign_assets:
            return {"form": "ITR-4", "name": "Sugam", "reason": "Presumptive business u/s 44AD/44ADA, income ≤ ₹50L"}
        return {"form": "ITR-3", "name": "Business & Profession", "reason": "Non-presumptive business income"}

    if has_cg or has_crypto:
        return {"form": "ITR-2", "name": "Capital Gains", "reason": "Capital gains or crypto income present"}
    if total > 5_000_000:
        return {"form": "ITR-2", "name": "Income > ₹50L", "reason": "Total income exceeds ₹50 Lakh"}
    if tax_input.has_foreign_assets:
        return {"form": "ITR-2", "name": "Foreign Assets", "reason": "Foreign assets require ITR-2"}
    if tax_input.is_director:
        return {"form": "ITR-2", "name": "Director", "reason": "Company director must file ITR-2"}
    if len(tax_input.properties) > 1:
        return {"form": "ITR-2", "name": "Multiple Properties", "reason": "Income from more than 1 house property"}
    if tax_input.has_unlisted_equity:
        return {"form": "ITR-2", "name": "Unlisted Equity", "reason": "Unlisted equity investments"}
    if tax_input.agricultural_income > 5_000:
        return {"form": "ITR-2", "name": "Agricultural Income", "reason": "Agricultural income > ₹5,000"}

    return {"form": "ITR-1", "name": "Sahaj", "reason": "Salaried individual, income ≤ ₹50L"}


# ─── Audit Checks ─────────────────────────────────────────────────────────────

def run_audit_checks(tax_input: TaxInput) -> tuple[list[dict], list[dict]]:
    """Pre-filing compliance audit. Returns (errors, warnings)."""
    errors: list[dict] = []
    warnings: list[dict] = []

    # 80C limit
    if tax_input.section_80c > 150_000:
        errors.append({"id": "80c_limit", "section": "Deductions",
                        "msg": f"80C deductions exceed ₹1,50,000 limit (claimed: ₹{tax_input.section_80c:,.0f})"})

    # HRA + 80GG conflict
    if tax_input.hra > 0 and tax_input.section_80gg > 0:
        errors.append({"id": "hra_80gg", "section": "Deductions",
                        "msg": "Cannot claim both HRA exemption and 80GG deduction"})

    # Crypto loss
    crypto_val = float(tax_input.capital_gains_detail.get("crypto_vda", 0))
    if crypto_val < 0:
        warnings.append({"id": "crypto_loss", "section": "Capital Gains",
                          "msg": "Crypto losses cannot be set off or carried forward"})

    # Advance tax
    gross = tax_input.salary + tax_input.business_income + tax_input.other_income
    if gross > 1_000_000 and tax_input.advance_tax_paid == 0:
        warnings.append({"id": "advance_tax", "section": "Compliance",
                          "msg": "Income > ₹10L — advance tax may apply (Sec 234B/234C)"})

    # Missing interest declaration
    if tax_input.interest_income == 0:
        warnings.append({"id": "interest_missing", "section": "Income",
                          "msg": "No savings/FD interest declared — verify with AIS"})

    return errors, warnings


# ─── Advance Tax Schedule ──────────────────────────────────────────────────────

def compute_advance_tax_schedule(total_tax: float) -> list[dict]:
    """Compute the 4 advance tax installments."""
    schedule = [
        {"installment": "1st", "due_date": "June 15", "cumulative_pct": 15},
        {"installment": "2nd", "due_date": "September 15", "cumulative_pct": 45},
        {"installment": "3rd", "due_date": "December 15", "cumulative_pct": 75},
        {"installment": "4th", "due_date": "March 15", "cumulative_pct": 100},
    ]
    for item in schedule:
        item["amount"] = round(total_tax * item["cumulative_pct"] / 100, 2)
    return schedule


# ─── Recommendation Engine ────────────────────────────────────────────────────

def generate_recommendations(
    tax_input: TaxInput,
    old: TaxBreakdown,
    new: TaxBreakdown,
) -> list[dict]:
    """Generate personalised tax-saving tips."""
    tips: list[dict] = []
    limits = DEDUCTION_LIMITS

    remaining_80c = max(0, limits["section_80c"] - tax_input.section_80c)
    if remaining_80c > 0:
        tips.append({
            "priority": "high",
            "title": f"Invest ₹{remaining_80c:,.0f} more under 80C",
            "desc": f"PPF/ELSS/LIC — potential savings of ₹{remaining_80c * 0.3:,.0f}",
            "potential_saving": round(remaining_80c * 0.3, 2),
        })

    remaining_nps = max(0, limits["section_80ccd_1b"] - tax_input.nps_80ccd)
    if remaining_nps > 0:
        tips.append({
            "priority": "high",
            "title": f"Add ₹{remaining_nps:,.0f} to NPS (80CCD(1B))",
            "desc": f"Additional NPS beyond 80C limit — save ₹{remaining_nps * 0.3:,.0f}",
            "potential_saving": round(remaining_nps * 0.3, 2),
        })

    if tax_input.section_80d == 0:
        tips.append({
            "priority": "critical",
            "title": "Get Health Insurance — Save up to ₹25,000 under 80D",
            "desc": "No health insurance claimed. Self + family deduction available.",
            "potential_saving": 25_000 * 0.3,
        })

    regime_diff = abs(old.total_tax - new.total_tax)
    if regime_diff > 1000:
        better = "Old" if old.total_tax < new.total_tax else "New"
        tips.append({
            "priority": "high",
            "title": f"Switch to {better} Regime — Save ₹{regime_diff:,.0f}",
            "desc": f"The {better} regime is more beneficial with your current deductions.",
            "potential_saving": round(regime_diff, 2),
        })

    # Sort by priority
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    tips.sort(key=lambda t: order.get(t["priority"], 3))
    return tips


# ─── Helper: Build TaxInput from JSONB data ───────────────────────────────────

def build_tax_input_from_itr_data(
    income_data: dict | None,
    deductions_data: dict | None,
    filing_details: dict | None,
) -> TaxInput:
    """
    Construct a TaxInput from the JSONB dictionaries stored in the ITRData model.
    This bridges the existing frontend data format to the engine's typed input.
    """
    inc = income_data or {}
    ded = deductions_data or {}
    fil = filing_details or {}

    def f(v: Any) -> float:
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0

    return TaxInput(
        salary=f(inc.get("salary")),
        house_property=f(inc.get("houseProperty")),
        business_income=f(inc.get("businessIncome")),
        capital_gains=f(inc.get("capitalGains")),
        other_income=f(inc.get("otherIncome")),
        interest_income=f(inc.get("interestIncome")),
        agricultural_income=f(inc.get("agriculturalIncome")),
        salary_components={k: f(v) for k, v in (inc.get("salary_components") or {}).items()},
        properties=inc.get("properties") or [],
        capital_gains_detail={k: f(v) for k, v in (inc.get("capital_gains_detail") or {}).items()},
        section_80c=f(ded.get("section80C")),
        nps_80ccd=f(ded.get("nps80CCD")),
        employer_nps=f(ded.get("employer_nps")),
        section_80d=f(ded.get("section80D")),
        section_80d_parents=f(ded.get("section80D_parents")),
        section_80e=f(ded.get("section80E")),
        section_80ee=f(ded.get("section80EE")),
        section_80eeb=f(ded.get("section80EEB")),
        section_80g=f(ded.get("section80G")),
        section_80gg=f(ded.get("section80GG")),
        section_80tta=f(ded.get("section80TTA")),
        section_80u=f(ded.get("section80U")),
        home_loan_interest=f(ded.get("homeLoanInterest")),
        hra=f(ded.get("hra")),
        advance_tax_paid=f(fil.get("advanceTaxPaid")),
        tds_deducted=f(fil.get("tdsDeducted")),
    )
