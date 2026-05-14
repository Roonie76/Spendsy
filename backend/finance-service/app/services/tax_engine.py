"""
Tax Computation Engine — Server-side source of truth for Indian Income Tax calculations.

Covers:
  - Old Regime (FY 2025-26): ₹2.5L / ₹5L / ₹10L slabs, 87A rebate ≤ ₹5L
  - New Regime (FY 2025-26 Budget): ₹4L / ₹8L / ₹12L / ₹16L / ₹20L / ₹24L, rebate ≤ ₹12L
  - Surcharge tiers with marginal relief
  - 4% Health & Education Cess
  - Full Chapter VI-A: 80C through 80U (all 25+ sections)
  - HRA exemption — 3-rule formula (Sec 10(13A))
  - 80GG — 3-way formula
  - 80D with preventive health check-up sub-limit
  - 80DD, 80DDB, 80EEA, 80G split (100%/50%/capped), 80GGA, 80GGC
  - Capital Gains: all 18 asset types, STCL/LTCL set-off matrix, 54/54EC/54F exemptions
  - House Property: 30% standard deduction on NAV, ₹2L loss cap, pre-construction interest
  - Presumptive taxation 44AD / 44ADA / 44AE
  - Agricultural income partial integration
  - Advance tax schedule + 234B/234C interest computation
  - ITR form selection logic (ITR-1 through ITR-7)
  - Family pension standard deduction
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional


# ─── Tax Constants ─────────────────────────────────────────────────────────────

# FY 2025-26 — new regime slabs (Union Budget 2025)
NEW_REGIME_SLABS_FY25_26 = [
    (400_000, 0.00),
    (800_000, 0.05),
    (1_200_000, 0.10),
    (1_600_000, 0.15),
    (2_000_000, 0.20),
    (2_400_000, 0.25),
    (float("inf"), 0.30),
]

# FY 2024-25 slabs
NEW_REGIME_SLABS_FY24_25 = [
    (300_000, 0.00),
    (700_000, 0.05),
    (1_000_000, 0.10),
    (1_200_000, 0.15),
    (1_500_000, 0.20),
    (float("inf"), 0.30),
]

# Old regime slabs — unchanged across FY24-25 and FY25-26
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

# Back-compat alias
NEW_REGIME_SLABS = NEW_REGIME_SLABS_FY25_26

NEW_REGIME_SLABS_BY_YEAR: dict[str, list[tuple[float, float]]] = {
    "FY25-26": NEW_REGIME_SLABS_FY25_26,
    "FY24-25": NEW_REGIME_SLABS_FY24_25,
}

NEW_REGIME_REBATE_BY_YEAR: dict[str, tuple[float, float]] = {
    "FY25-26": (1_200_000, 60_000),
    "FY24-25": (700_000, 25_000),
}

OLD_REGIME_STD_DED_BY_YEAR: dict[str, float] = {
    "FY25-26": 50_000,
    "FY24-25": 50_000,
}

NEW_REGIME_STD_DED_BY_YEAR: dict[str, float] = {
    "FY25-26": 75_000,
    "FY24-25": 75_000,
}

CURRENT_FY = "FY25-26"

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
    "section_80d_preventive": 5_000,
    "section_80dd": 75_000,
    "section_80dd_severe": 125_000,
    "section_80ddb": 40_000,
    "section_80ddb_senior": 100_000,
    "section_80e": None,               # No limit
    "section_80ee": 50_000,
    "section_80eea": 150_000,
    "section_80eeb": 150_000,
    "section_80gg_monthly": 5_000,
    "section_80gga": None,             # No limit
    "section_80ggc": None,             # No limit (non-cash)
    "section_80tta": 10_000,
    "section_80ttb_senior": 50_000,
    "section_80u": 75_000,
    "section_80u_severe": 125_000,
    "section_24b_sop": 200_000,
    "family_pension_std_ded": 15_000,
}

CG_RATES = {
    "stcg_111a": 0.20,
    "ltcg_112a": 0.125,
    "ltcg_112a_exempt": 125_000,
    "ltcg_112": 0.125,
    "crypto_vda": 0.30,
    "lottery_115bb": 0.30,
    "intraday_speculative": 0.30,      # taxed at slab, but tracked separately
}

# Basic exemption limits by age category (old regime)
BASIC_EXEMPTION = {
    "general": 250_000,
    "senior": 300_000,
    "super_senior": 500_000,
}


# ─── Capital Gains Detail Dataclass ───────────────────────────────────────────

@dataclass
class CapitalGainsDetail:
    """All 18 asset types + losses for full CG computation."""
    # Section 111A — 20% (listed equity + equity MF STCG)
    listed_equity_stcg: float = 0
    equity_mf_stcg: float = 0

    # Section 112A — 12.5% above ₹1.25L (listed equity + equity MF LTCG)
    listed_equity_ltcg: float = 0
    equity_mf_ltcg: float = 0

    # Debt MF — post Apr-2023 units: slab rate
    debt_mf_stcg: float = 0
    # Debt MF — pre Apr-2023 units held > 24m: 12.5%
    debt_mf_ltcg_old: float = 0

    # Real estate STCG (≤24m) — slab rate
    property_stcg: float = 0
    # Real estate LTCG — post 23-Jul-2024 transfers: 12.5% no indexation
    property_ltcg_post: float = 0
    # Real estate LTCG — pre 23-Jul-2024 transfers: user choice (12.5% or 20%+indexation)
    property_ltcg_pre: float = 0
    property_ltcg_pre_uses_indexation: bool = False   # True = 20%+idx, False = 12.5%

    # Gold / jewellery
    gold_stcg: float = 0              # ≤24m — slab rate
    gold_ltcg: float = 0              # >24m — 12.5%

    # Sovereign Gold Bond — if held to maturity via RBI: exempt; via exchange: 112A
    sgb_ltcg: float = 0               # via exchange — 12.5%
    sgb_maturity_exempt: float = 0    # maturity redemption — fully exempt

    # Crypto / VDA — Section 115BBH — 30%, no set-off ever
    crypto_vda: float = 0

    # Unlisted shares
    unlisted_stcg: float = 0          # ≤24m — slab rate
    unlisted_ltcg: float = 0          # >24m — 12.5%

    # Bonds
    bonds_stcg: float = 0             # ≤12m — slab rate
    bonds_ltcg: float = 0             # >12m listed — 12.5%

    # Losses (enter as positive numbers; engine treats as negative)
    stcl: float = 0                   # Short-term capital loss
    ltcl: float = 0                   # Long-term capital loss

    # Intraday speculative
    speculative_profit: float = 0
    speculative_loss: float = 0


@dataclass
class CGExemptions:
    """Section 54 / 54EC / 54F capital gains exemptions."""
    # Sec 54: LTCG on residential house property → reinvest in new residential house
    sec54_ltcg_reinvested: float = 0

    # Sec 54EC: LTCG on property → NHAI/REC bonds (max ₹50L)
    sec54ec_bonds_invested: float = 0

    # Sec 54F: LTCG on non-residential asset → net consideration invested in house
    sec54f_consideration_invested: float = 0
    sec54f_net_consideration: float = 0    # total sale consideration


# ─── Main TaxInput Dataclass ──────────────────────────────────────────────────

@dataclass
class TaxInput:
    """All user inputs needed for complete tax computation."""

    # ── Income heads ─────────────────────────────────────────────────────────
    salary: float = 0
    house_property: float = 0          # fallback scalar if properties list empty
    business_income: float = 0
    capital_gains: float = 0           # fallback scalar if cg_detail empty
    other_income: float = 0
    interest_income: float = 0         # savings / FD interest
    agricultural_income: float = 0
    family_pension: float = 0          # family pension — std deduction of min(1/3, 15000)
    lottery_income: float = 0          # Section 115BB — 30%
    dividend_income: float = 0         # taxed at slab rate

    # ── Salary components (optional granular breakup) ─────────────────────
    salary_components: dict[str, float] = field(default_factory=dict)

    # ── HRA detailed inputs (required for proper HRA formula) ────────────
    basic_salary: float = 0            # basic salary (for HRA + EPF computation)
    hra_received: float = 0            # actual HRA component received from employer
    rent_paid: float = 0               # annual rent paid

    # ── House property details ────────────────────────────────────────────
    properties: list[dict[str, Any]] = field(default_factory=list)
    pre_construction_interest: float = 0   # total interest paid during construction
    pre_construction_year: int = 0         # year number (1-5) after possession

    # ── Capital gains ─────────────────────────────────────────────────────
    capital_gains_detail: dict[str, float] = field(default_factory=dict)
    # Structured CG detail (preferred over dict above when populated)
    cg_detail: Optional[CapitalGainsDetail] = None
    cg_exemptions: Optional[CGExemptions] = None

    # ── Standard deductions ───────────────────────────────────────────────
    section_80c: float = 0             # aggregate of all 80C instruments
    # 80C sub-items (tracked for gap analysis; sum must not exceed 1.5L)
    _80c_epf: float = 0
    _80c_ppf: float = 0
    _80c_elss: float = 0
    _80c_lic: float = 0
    _80c_nsc: float = 0
    _80c_fd: float = 0
    _80c_principal: float = 0          # home loan principal
    _80c_stamp_duty: float = 0
    _80c_tuition: float = 0
    _80c_scss: float = 0
    _80c_sukanya: float = 0
    _80c_annuity: float = 0            # 80CCC annuity plan

    nps_80ccd: float = 0               # 80CCD(1B) — additional NPS beyond 80C
    employer_nps: float = 0            # 80CCD(2) — both regimes

    # 80D
    section_80d: float = 0             # health insurance self + family
    section_80d_preventive: float = 0  # preventive health check-up (sub-limit ₹5K)
    section_80d_parents: float = 0     # health insurance parents
    section_80d_parents_preventive: float = 0

    # 80DD — dependent with disability (fixed deduction)
    section_80dd: float = 0            # enter 75000 or 125000
    section_80dd_severity: str = "normal"  # "normal" | "severe"

    # 80DDB — treatment of specified disease
    section_80ddb: float = 0           # actual expenditure; engine applies age cap

    # 80E — education loan interest
    section_80e: float = 0

    # 80EE / 80EEA / 80EEB
    section_80ee: float = 0
    section_80eea: float = 0
    section_80eea_eligible: bool = False    # loan sanctioned Apr19-Mar22, stamp ≤45L
    section_80eeb: float = 0

    # 80G — donations (split into 3 buckets for correct computation)
    section_80g: float = 0             # back-compat: legacy combined amount
    section_80g_100pct: float = 0      # 100% eligible (PMNRF, PM CARES, etc.) — no cap
    section_80g_50pct: float = 0       # 50% eligible (approved charities) — no cap
    section_80g_capped: float = 0      # 50% eligible, 10% GTI cap institutions

    # 80GGA — scientific research / rural development
    section_80gga: float = 0

    # 80GGC — political parties (non-cash only)
    section_80ggc: float = 0

    # 80GG — rent without HRA (formula-computed; input rent_paid above)
    section_80gg: float = 0            # back-compat override; if 0, formula is used

    # 80TTA / 80TTB
    section_80tta: float = 0

    # 80U — own disability
    section_80u: float = 0
    section_80u_severity: str = "normal"    # "normal" | "severe"

    # 24(b)
    home_loan_interest: float = 0
    hra: float = 0                     # HRA exemption override (if 0, formula used)

    # LTA
    lta_claimed: float = 0

    # ── Profile ───────────────────────────────────────────────────────────
    age: int = 30
    is_presumptive: bool = False
    business_type: str = "44ADA"       # "44AD" | "44ADA" | "44AE" | "regular"
    business_turnover: float = 0       # for 44AD
    profession_receipts: float = 0     # for 44ADA
    is_metro: bool = False
    parents_are_senior: bool = False
    is_nri: bool = False
    has_foreign_assets: bool = False
    is_director: bool = False
    has_unlisted_equity: bool = False
    entity_type: str = "individual"

    # ── Filing ────────────────────────────────────────────────────────────
    advance_tax_paid: float = 0        # total advance tax paid (all quarters)
    advance_tax_q1: float = 0          # 15 Jun
    advance_tax_q2: float = 0          # 15 Sep
    advance_tax_q3: float = 0          # 15 Dec
    advance_tax_q4: float = 0          # 15 Mar
    tds_deducted: float = 0

    # ── Financial year ────────────────────────────────────────────────────
    fy: str = CURRENT_FY


# ─── Output Dataclasses ───────────────────────────────────────────────────────

@dataclass
class TaxBreakdown:
    """Detailed output of tax computation for one regime."""
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
    # Additional breakdowns for UI waterfall
    slab_cg_income: float = 0          # CG taxed at slab rate (debt MF, property STCG etc.)
    hp_income: float = 0
    pre_construction_ded: float = 0


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
    # Interest penalties
    interest_234b: float = 0
    interest_234c: float = 0


@dataclass
class VerificationResult:
    """Result of hash chain integrity verification."""
    intact: bool
    total_events: int
    broken_at_event_id: Optional[int]
    break_reason: Optional[str]
    submission_hash_match: bool
    computed_hash: str
    stored_hash: str
    verified_at: str


# ─── Formula Functions ────────────────────────────────────────────────────────

def compute_hra_exemption(
    basic_salary: float,
    hra_received: float,
    rent_paid: float,
    is_metro: bool,
) -> float:
    """
    HRA exemption u/s 10(13A) — minimum of three rules:
      Rule 1: Actual HRA received from employer
      Rule 2: Actual rent paid − 10% of basic salary
      Rule 3: 50% of basic (metro) / 40% of basic (non-metro)
    Returns 0 if rent_paid <= 0 or hra_received <= 0.
    """
    if rent_paid <= 0 or hra_received <= 0:
        return 0.0
    rule1 = hra_received
    rule2 = max(0.0, rent_paid - basic_salary * 0.10)
    rule3 = basic_salary * (0.50 if is_metro else 0.40)
    return max(0.0, min(rule1, rule2, rule3))


def compute_80gg(rent_paid: float, adjusted_gti: float) -> float:
    """
    80GG deduction — minimum of three rules:
      Rule 1: ₹5,000 per month (₹60,000/year)
      Rule 2: 25% of adjusted gross total income
      Rule 3: Rent paid − 10% of adjusted GTI
    Only applicable when no HRA received and taxpayer doesn't own residential property.
    """
    if rent_paid <= 0 or adjusted_gti <= 0:
        return 0.0
    rule1 = 5_000 * 12
    rule2 = adjusted_gti * 0.25
    rule3 = max(0.0, rent_paid - adjusted_gti * 0.10)
    return min(rule1, rule2, rule3)


def compute_80d(
    premium_self: float,
    preventive_self: float,
    premium_parents: float,
    preventive_parents: float,
    age_self: int,
    parents_are_senior: bool,
) -> tuple[float, float]:
    """
    80D deduction with preventive health check-up sub-limit (₹5,000).
    Returns (deduction_self, deduction_parents).
    """
    limits = DEDUCTION_LIMITS
    limit_self = limits["section_80d_self_senior"] if age_self >= 60 else limits["section_80d_self"]
    limit_parents = limits["section_80d_parents_senior"] if parents_are_senior else limits["section_80d_parents"]
    preventive_limit = limits["section_80d_preventive"]  # ₹5,000

    # Self: insurance premium + preventive (preventive capped at ₹5K within limit_self)
    preventive_self_allowed = min(preventive_self, preventive_limit)
    ded_self = min(premium_self + preventive_self_allowed, limit_self)

    # Parents: same logic
    preventive_parents_allowed = min(preventive_parents, preventive_limit)
    ded_parents = min(premium_parents + preventive_parents_allowed, limit_parents)

    return ded_self, ded_parents


def compute_80g(
    donations_100pct: float,
    donations_50pct: float,
    donations_capped: float,
    adjusted_gti: float,
) -> float:
    """
    80G deduction across three buckets:
      - 100% eligible (PMNRF, PM CARES, National Defence Fund): no cap
      - 50% eligible (approved charities, temples): 50% of donation, no GTI cap
      - Capped institutions: 50% of donation, capped at 10% of adjusted GTI
    """
    d100 = max(0.0, donations_100pct)
    d50 = max(0.0, donations_50pct) * 0.50
    d_cap_eligible = min(donations_capped, adjusted_gti * 0.10)
    d_capped = d_cap_eligible * 0.50
    return d100 + d50 + d_capped


def compute_sec54_exemption(
    ltcg_residential: float,
    reinvested: float,
) -> float:
    """
    Section 54 exemption: LTCG on sale of residential house property.
    Exempt amount = min(LTCG, amount reinvested in new residential house within 2yr).
    """
    return min(max(0.0, ltcg_residential), max(0.0, reinvested))


def compute_sec54ec_exemption(
    ltcg_property: float,
    bonds_invested: float,
) -> float:
    """
    Section 54EC: LTCG on property → NHAI/REC bonds within 6 months.
    Max exemption ₹50L.
    """
    return min(max(0.0, ltcg_property), min(bonds_invested, 50_000_000))


def compute_sec54f_exemption(
    ltcg_other: float,
    net_consideration: float,
    amount_invested: float,
) -> float:
    """
    Section 54F: LTCG on any non-residential asset → invested in residential house.
    Proportional exemption if not fully invested.
    """
    if net_consideration <= 0:
        return 0.0
    invested = min(amount_invested, net_consideration)
    return ltcg_other * (invested / net_consideration)


def compute_pre_construction_interest(
    total_pre_construction_interest: float,
    year: int,
) -> float:
    """
    Pre-construction interest deduction u/s 24(b).
    1/5th of total pre-construction interest per year, for 5 years after possession.
    Subject to overall ₹2L SOP cap.
    year: 1..5 (after construction completion year)
    """
    if year < 1 or year > 5 or total_pre_construction_interest <= 0:
        return 0.0
    return total_pre_construction_interest / 5.0


def compute_234b_interest(
    total_tax: float,
    tds_deducted: float,
    advance_tax_paid: float,
    months_elapsed: int,
) -> float:
    """
    234B interest: if advance tax paid < 90% of assessed tax.
    1% per month on shortfall from Apr 1 to date of assessment.
    """
    assessed_tax = max(0.0, total_tax - tds_deducted)
    if assessed_tax <= 10_000:
        return 0.0  # Advance tax not applicable below ₹10K liability
    required = assessed_tax * 0.90
    if advance_tax_paid >= required:
        return 0.0
    shortfall = assessed_tax - advance_tax_paid
    return round(shortfall * 0.01 * max(1, months_elapsed), 2)


def compute_234c_interest(
    quarterly_paid: list[float],
    total_tax: float,
    tds_deducted: float,
) -> float:
    """
    234C interest: deferment of advance tax installments.
    Checks each quarterly target; 1% per month on shortfall.
    quarterly_paid: [q1, q2, q3, q4] amounts paid at each installment date.
    """
    assessed = max(0.0, total_tax - tds_deducted)
    if assessed <= 10_000:
        return 0.0
    targets = [0.15, 0.45, 0.75, 1.00]
    months = [3, 3, 3, 1]              # interest months per installment
    interest = 0.0
    for i, target in enumerate(targets):
        required = assessed * target
        paid_so_far = sum(quarterly_paid[:i + 1])
        if paid_so_far < required:
            shortfall = required - paid_so_far
            interest += shortfall * 0.01 * months[i]
    return round(interest, 2)


def _compute_presumptive_income(tax_input: TaxInput) -> float:
    """Compute deemed profit for presumptive taxation."""
    bt = tax_input.business_type
    if bt == "44AD":
        # 6% of digital turnover, 8% of cash turnover
        # Simplified: 6% if is_presumptive flag set (assume digital)
        t = tax_input.business_turnover or tax_input.business_income
        if t <= 30_000_000:
            return t * 0.06
        return t  # Above limit: regular books
    elif bt == "44ADA":
        r = tax_input.profession_receipts or tax_input.business_income
        if r <= 7_500_000:
            return r * 0.50
        return r
    elif bt == "44AE":
        # ₹7,500/month per light vehicle; simplified as 44ADA proxy
        return tax_input.business_income
    else:
        return tax_input.business_income


def _apply_cg_setoff(detail: dict[str, float]) -> tuple[float, float, float, float]:
    """
    Apply STCL / LTCL set-off rules.
    Returns: (stcg_net, ltcg_net, slab_cg_net, stcl_cf, ltcl_cf)
    STCL offsets STCG first, then LTCG.
    LTCL offsets LTCG only.
    Crypto loss: no set-off at all.
    """
    def f(k: str) -> float:
        return max(0.0, float(detail.get(k, 0)))

    stcg_111a = f("listed_equity_stcg") + f("equity_mf_stcg")
    ltcg_112a = f("listed_equity_ltcg") + f("equity_mf_ltcg")
    ltcg_other = (f("debt_mf_ltcg_old") + f("property_ltcg_post") + f("property_ltcg_pre")
                  + f("gold_ltcg") + f("sgb_ltcg") + f("unlisted_ltcg") + f("bonds_ltcg"))
    slab_cg = (f("debt_mf_stcg") + f("property_stcg") + f("gold_stcg")
               + f("unlisted_stcg") + f("bonds_stcg"))
    # Crypto excluded from set-off
    crypto = f("crypto_vda")
    stcl = abs(float(detail.get("stcl", 0)))
    ltcl = abs(float(detail.get("ltcl", 0)))

    total_stcg = stcg_111a + slab_cg
    total_ltcg = ltcg_112a + ltcg_other

    # STCL offsets STCG first
    stcl_remaining = max(0.0, stcl - total_stcg)
    stcg_net = max(0.0, total_stcg - stcl)
    # Then remaining STCL offsets LTCG
    ltcg_after_stcl = max(0.0, total_ltcg - stcl_remaining)
    # LTCL offsets remaining LTCG only
    ltcg_net = max(0.0, ltcg_after_stcl - ltcl)

    # Re-split stcg_net proportionally
    if total_stcg > 0:
        stcg_111a_net = stcg_net * (stcg_111a / total_stcg)
        slab_cg_net = stcg_net * (slab_cg / total_stcg)
    else:
        stcg_111a_net = 0.0
        slab_cg_net = 0.0

    # Split ltcg_net between 112A and other proportionally
    if total_ltcg > 0:
        ltcg_112a_net = ltcg_net * (ltcg_112a / total_ltcg)
        ltcg_other_net = ltcg_net * (ltcg_other / total_ltcg)
    else:
        ltcg_112a_net = 0.0
        ltcg_other_net = 0.0

    return stcg_111a_net, ltcg_112a_net, ltcg_other_net, slab_cg_net, crypto


# ─── Capital Gains Tax Computation ────────────────────────────────────────────

def _compute_capital_gains_tax(
    detail: dict[str, float],
    cg_exemptions: Optional[CGExemptions] = None,
) -> tuple[float, float]:
    """
    Compute capital gains tax.
    Returns: (cg_tax_with_cess, slab_cg_income)
    slab_cg_income is added back to taxable income for slab computation.
    """
    stcg_111a, ltcg_112a, ltcg_other, slab_cg, crypto = _apply_cg_setoff(detail)

    # Apply Sec 54 / 54EC / 54F exemptions to LTCG
    if cg_exemptions:
        ltcg_other = max(0.0, ltcg_other - cg_exemptions.sec54_ltcg_reinvested)
        ltcg_other = max(0.0, ltcg_other - cg_exemptions.sec54ec_bonds_invested)
        if cg_exemptions.sec54f_net_consideration > 0:
            exempt_54f = (ltcg_other * cg_exemptions.sec54f_consideration_invested
                          / cg_exemptions.sec54f_net_consideration)
            ltcg_other = max(0.0, ltcg_other - exempt_54f)

    cg_tax = 0.0

    # STCG 111A — 20%
    if stcg_111a > 0:
        cg_tax += stcg_111a * CG_RATES["stcg_111a"]

    # LTCG 112A — 12.5% above ₹1.25L exemption
    if ltcg_112a > CG_RATES["ltcg_112a_exempt"]:
        cg_tax += (ltcg_112a - CG_RATES["ltcg_112a_exempt"]) * CG_RATES["ltcg_112a"]

    # LTCG 112 (other assets) — 12.5%
    if ltcg_other > 0:
        cg_tax += ltcg_other * CG_RATES["ltcg_112"]

    # Crypto — 30%, no cess deduction, no set-off
    if crypto > 0:
        cg_tax += crypto * CG_RATES["crypto_vda"]

    # Lottery — 30%
    lottery = float(detail.get("lottery_income", 0))
    if lottery > 0:
        cg_tax += lottery * CG_RATES["lottery_115bb"]

    # 4% cess on CG tax
    cg_tax_with_cess = cg_tax * (1 + CESS_RATE)

    return cg_tax_with_cess, slab_cg


# ─── House Property Computation ───────────────────────────────────────────────

def _compute_house_property_income(
    properties: list[dict],
    hp_value: float,
    regime: str = "old",
    pre_construction_interest: float = 0,
    pre_construction_year: int = 0,
) -> tuple[float, float]:
    """
    Compute net income from house property.
    Returns: (hp_income, pre_construction_ded)
    New regime: HP loss cannot be set off against other income.
    """
    if not properties:
        return hp_value, 0.0

    total = 0.0
    pre_con_ded = 0.0

    for prop in properties:
        prop_type = prop.get("property_type", "self_occupied")
        loan_interest = float(prop.get("loan_interest", 0))

        if prop_type == "self_occupied":
            # Capped at ₹2L for SOP
            interest_ded = min(loan_interest, DEDUCTION_LIMITS["section_24b_sop"])
            total -= interest_ded
        else:
            # Let-out or deemed let-out
            rent = float(prop.get("annual_rent", 0))
            municipal = float(prop.get("municipal_tax", 0))
            vacancy_months = int(prop.get("vacancy_months", 0))
            # Adjust rent for vacancy
            if vacancy_months > 0:
                rent = rent * ((12 - vacancy_months) / 12)
            nav = max(0.0, rent - municipal)
            std_ded = nav * 0.30
            # No limit on interest for let-out
            total += nav - std_ded - loan_interest

    # Pre-construction interest: 1/5th per year for 5 years after possession
    if pre_construction_interest > 0 and 1 <= pre_construction_year <= 5:
        pre_con_ded = pre_construction_interest / 5.0
        total -= pre_con_ded

    # Loss cap at ₹2L for set-off against other heads
    if total < -200_000:
        # Excess carried forward (not modelled here — just capped)
        total = -200_000

    # New regime: HP loss not allowed against salary/other
    if regime == "new" and total < 0:
        total = 0.0

    return total, pre_con_ded


# ─── Agricultural Income Partial Integration ──────────────────────────────────

def _compute_partial_integration_tax(
    taxable_income: float,
    agri_income: float,
    age: int,
    slabs: list[tuple[float, float]],
) -> float:
    """
    Agricultural income partial integration for rate purposes.
    Applicable when: agri_income > ₹5,000 AND total income > basic exemption.
    Tax = slab_tax(taxable + agri) - slab_tax(agri + basic_exemption)
    """
    if agri_income <= 5_000:
        return 0.0
    age_cat = "super_senior" if age >= 80 else ("senior" if age >= 60 else "general")
    basic_exempt = BASIC_EXEMPTION[age_cat]
    if taxable_income <= basic_exempt:
        return 0.0
    tax_combined = _slab_tax(taxable_income + agri_income, slabs)
    tax_agri_only = _slab_tax(agri_income + basic_exempt, slabs)
    return max(0.0, tax_combined - tax_agri_only)


# ─── Core Slab + Surcharge ────────────────────────────────────────────────────

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


# ─── Main Tax Computation ─────────────────────────────────────────────────────

def compute_tax(tax_input: TaxInput, regime: str = "new") -> TaxBreakdown:
    """
    Compute full tax liability under the specified regime.
    """
    fy = tax_input.fy if tax_input.fy in NEW_REGIME_SLABS_BY_YEAR else CURRENT_FY

    # ── 1. Gross salary ────────────────────────────────────────────────────
    gross_salary = tax_input.salary
    if tax_input.salary_components:
        from_components = sum(
            v for k, v in tax_input.salary_components.items()
            if k not in ("epf_employer", "nps_employer", "professional_tax",
                         "gratuity", "leave_encashment", "lta")
        )
        if from_components > 0:
            gross_salary = from_components

    # ── 2. HRA exemption ──────────────────────────────────────────────────
    if regime == "old":
        if tax_input.hra > 0:
            # Legacy override: use directly
            hra_exempt = tax_input.hra
        elif tax_input.hra_received > 0 and tax_input.rent_paid > 0:
            hra_exempt = compute_hra_exemption(
                tax_input.basic_salary or gross_salary * 0.40,  # fallback: 40% of gross
                tax_input.hra_received,
                tax_input.rent_paid,
                tax_input.is_metro,
            )
        else:
            hra_exempt = 0.0
    else:
        hra_exempt = 0.0  # HRA not allowed in new regime

    # ── 3. House property income ───────────────────────────────────────────
    hp_income, pre_con_ded = _compute_house_property_income(
        tax_input.properties,
        tax_input.house_property,
        regime=regime,
        pre_construction_interest=tax_input.pre_construction_interest,
        pre_construction_year=tax_input.pre_construction_year,
    )

    # ── 4. Business income ─────────────────────────────────────────────────
    if tax_input.is_presumptive:
        business = _compute_presumptive_income(tax_input)
    else:
        business = tax_input.business_income

    # ── 5. Family pension std deduction ───────────────────────────────────
    family_pension_ded = 0.0
    if tax_input.family_pension > 0:
        family_pension_ded = min(
            tax_input.family_pension / 3.0,
            DEDUCTION_LIMITS["family_pension_std_ded"],
        )

    # ── 6. Gross total income (excl CG — taxed separately) ────────────────
    gti = (gross_salary
           + hp_income
           + business
           + tax_input.other_income
           + tax_input.interest_income
           + tax_input.dividend_income
           + max(0.0, tax_input.family_pension - family_pension_ded))

    # ── 7. Standard deduction ─────────────────────────────────────────────
    if regime == "new":
        std_ded = NEW_REGIME_STD_DED_BY_YEAR[fy] if gross_salary > 0 else 0
    else:
        std_ded = OLD_REGIME_STD_DED_BY_YEAR[fy] if gross_salary > 0 else 0

    # ── 8. Chapter VI-A deductions ─────────────────────────────────────────
    total_deductions = std_ded

    if regime == "old":
        limits = DEDUCTION_LIMITS
        adjusted_gti = max(0.0, gti - std_ded)   # for 80GG/80G cap purposes

        # 80C
        total_deductions += min(tax_input.section_80c, limits["section_80c"])

        # 80CCD(1B)
        total_deductions += min(tax_input.nps_80ccd, limits["section_80ccd_1b"])

        # 80D (with preventive sub-limit)
        ded_80d_self, ded_80d_parents = compute_80d(
            tax_input.section_80d,
            tax_input.section_80d_preventive,
            tax_input.section_80d_parents,
            tax_input.section_80d_parents_preventive,
            tax_input.age,
            tax_input.parents_are_senior,
        )
        total_deductions += ded_80d_self + ded_80d_parents

        # 80DD (fixed — certificate required)
        if tax_input.section_80dd > 0:
            limit_80dd = limits["section_80dd_severe"] if tax_input.section_80dd_severity == "severe" else limits["section_80dd"]
            total_deductions += limit_80dd

        # 80DDB (age-aware)
        if tax_input.section_80ddb > 0:
            limit_80ddb = limits["section_80ddb_senior"] if tax_input.age >= 60 else limits["section_80ddb"]
            total_deductions += min(tax_input.section_80ddb, limit_80ddb)

        # 80E — no limit
        total_deductions += tax_input.section_80e

        # 80EE
        total_deductions += min(tax_input.section_80ee, limits["section_80ee"])

        # 80EEA (affordable housing — eligibility check)
        if tax_input.section_80eea_eligible:
            total_deductions += min(tax_input.section_80eea, limits["section_80eea"])

        # 80EEB
        total_deductions += min(tax_input.section_80eeb, limits["section_80eeb"])

        # 80G (split computation)
        if tax_input.section_80g_100pct + tax_input.section_80g_50pct + tax_input.section_80g_capped > 0:
            total_deductions += compute_80g(
                tax_input.section_80g_100pct,
                tax_input.section_80g_50pct,
                tax_input.section_80g_capped,
                adjusted_gti,
            )
        elif tax_input.section_80g > 0:
            # Back-compat: treat legacy 80G as 50% eligible (conservative)
            total_deductions += tax_input.section_80g * 0.50

        # 80GGA (scientific research donations — no business income required)
        if tax_input.section_80gga > 0 and tax_input.business_income == 0:
            total_deductions += tax_input.section_80gga

        # 80GGC (political parties — non-cash)
        total_deductions += tax_input.section_80ggc

        # 80GG (rent without HRA — formula)
        if tax_input.hra_received <= 0 and tax_input.rent_paid > 0:
            if tax_input.section_80gg > 0:
                total_deductions += min(tax_input.section_80gg, limits["section_80gg_monthly"] * 12)
            else:
                total_deductions += compute_80gg(tax_input.rent_paid, adjusted_gti)

        # 80TTA / 80TTB
        if tax_input.age >= 60:
            total_deductions += min(tax_input.section_80tta, limits["section_80ttb_senior"])
        else:
            total_deductions += min(tax_input.section_80tta, limits["section_80tta"])

        # 80U (fixed — disability certificate required)
        if tax_input.section_80u > 0:
            limit_80u = limits["section_80u_severe"] if tax_input.section_80u_severity == "severe" else limits["section_80u"]
            total_deductions += limit_80u

        # HRA exemption (already computed above)
        total_deductions += hra_exempt

        # 24(b) home loan interest
        if tax_input.properties:
            # Already included in HP income computation
            pass
        else:
            total_deductions += min(tax_input.home_loan_interest, limits["section_24b_sop"])

    # 80CCD(2) — employer NPS — BOTH regimes
    total_deductions += tax_input.employer_nps

    # ── 9. Taxable income ──────────────────────────────────────────────────
    taxable_income = max(0.0, gti - total_deductions)

    # ── 10. Agricultural income partial integration ────────────────────────
    # Pick slabs first (needed for partial integration)
    if regime == "new":
        slabs = NEW_REGIME_SLABS_BY_YEAR[fy]
        max_surcharge_rate = 0.25
        rebate_limit, rebate_max = NEW_REGIME_REBATE_BY_YEAR[fy]
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

    # ── 11. Base tax from slabs ────────────────────────────────────────────
    base_tax = _slab_tax(taxable_income, slabs)

    # Agricultural income partial integration (old regime only)
    if regime == "old" and tax_input.agricultural_income > 5_000:
        base_tax = _compute_partial_integration_tax(
            taxable_income, tax_input.agricultural_income, tax_input.age, slabs
        )
        # Re-use: override base_tax with integrated computation
        base_tax = max(base_tax, _slab_tax(taxable_income, slabs))

    # ── 12. Rebate u/s 87A ─────────────────────────────────────────────────
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

    # ── 13. Surcharge with marginal relief ────────────────────────────────
    surcharge, surcharge_rate = _compute_surcharge(base_tax, taxable_income, max_surcharge_rate, slabs)

    # ── 14. Cess ──────────────────────────────────────────────────────────
    cess = (base_tax + surcharge) * CESS_RATE

    # ── 15. Capital gains tax ─────────────────────────────────────────────
    cg_detail = tax_input.capital_gains_detail or {}
    cg_tax, slab_cg_income = _compute_capital_gains_tax(
        cg_detail,
        tax_input.cg_exemptions,
    )

    # ── 16. Lottery income (30%) ──────────────────────────────────────────
    lottery_tax = tax_input.lottery_income * CG_RATES["lottery_115bb"] * (1 + CESS_RATE)

    # ── 17. Total ─────────────────────────────────────────────────────────
    total_tax = base_tax + surcharge + cess + cg_tax + lottery_tax

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
        capital_gains_tax=cg_tax + lottery_tax,
        total_tax=total_tax,
        effective_rate=round(effective_rate, 2),
        rebate_applied=rebate_applied,
        slab_cg_income=slab_cg_income,
        hp_income=hp_income,
        pre_construction_ded=pre_con_ded,
    )


# ─── Regime Comparison ─────────────────────────────────────────────────────────

def compare_regimes(tax_input: TaxInput) -> RegimeComparison:
    """Compute tax under both regimes and return a full comparison."""
    old = compute_tax(tax_input, "old")
    new = compute_tax(tax_input, "new")

    recommended = "new" if new.total_tax <= old.total_tax else "old"
    savings = abs(old.total_tax - new.total_tax)

    # Breakeven: additional old-regime deductions needed to equal new regime
    breakeven = 0.0
    if recommended == "new" and old.taxable_income > 0:
        # Compute marginal rate in old regime
        marginal_rate = _get_marginal_rate(old.taxable_income, old.surcharge_rate)
        breakeven = (savings / marginal_rate) if marginal_rate > 0 else 0

    itr_form = determine_itr_form(tax_input)
    errors, warnings = run_audit_checks(tax_input)
    schedule = compute_advance_tax_schedule(max(old.total_tax, new.total_tax))
    tips = generate_recommendations(tax_input, old, new)

    # 234B/C interest (on recommended regime tax)
    chosen_tax = new.total_tax if recommended == "new" else old.total_tax
    q_paid = [
        tax_input.advance_tax_q1,
        tax_input.advance_tax_q2,
        tax_input.advance_tax_q3,
        tax_input.advance_tax_q4,
    ]
    total_adv = sum(q_paid) or tax_input.advance_tax_paid
    today = date.today()
    months_elapsed = max(1, (today.month - 3) % 12)  # months since Apr 1
    i234b = compute_234b_interest(chosen_tax, tax_input.tds_deducted, total_adv, months_elapsed)
    i234c = compute_234c_interest(q_paid, chosen_tax, tax_input.tds_deducted)

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
        interest_234b=i234b,
        interest_234c=i234c,
    )


def _get_marginal_rate(taxable_income: float, surcharge_rate: float) -> float:
    """Estimate effective marginal rate including surcharge and cess."""
    for limit, rate in OLD_REGIME_SLABS:
        if taxable_income <= limit:
            marginal = rate
            break
    else:
        marginal = 0.30
    return marginal * (1 + surcharge_rate) * (1 + CESS_RATE)


# ─── ITR Form Selection ───────────────────────────────────────────────────────

def determine_itr_form(tax_input: TaxInput) -> dict[str, str]:
    """Choose the correct ITR form based on income profile."""
    salary = tax_input.salary
    business = tax_input.business_income
    cg = tax_input.capital_gains
    cg_detail = tax_input.capital_gains_detail or {}
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
        if (tax_input.is_presumptive and total <= 5_000_000
                and not has_cg and not tax_input.has_foreign_assets):
            return {"form": "ITR-4", "name": "Sugam",
                    "reason": "Presumptive business u/s 44AD/44ADA, income ≤ ₹50L"}
        return {"form": "ITR-3", "name": "Business & Profession",
                "reason": "Non-presumptive business income"}

    if has_cg or has_crypto:
        return {"form": "ITR-2", "name": "Capital Gains",
                "reason": "Capital gains or crypto income present"}
    if total > 5_000_000:
        return {"form": "ITR-2", "name": "Income > ₹50L",
                "reason": "Total income exceeds ₹50 Lakh"}
    if tax_input.has_foreign_assets:
        return {"form": "ITR-2", "name": "Foreign Assets",
                "reason": "Foreign assets require ITR-2"}
    if tax_input.is_director:
        return {"form": "ITR-2", "name": "Director",
                "reason": "Company director must file ITR-2"}
    if len(tax_input.properties) > 1:
        return {"form": "ITR-2", "name": "Multiple Properties",
                "reason": "Income from more than 1 house property"}
    if tax_input.has_unlisted_equity:
        return {"form": "ITR-2", "name": "Unlisted Equity",
                "reason": "Unlisted equity investments"}
    if tax_input.agricultural_income > 5_000:
        return {"form": "ITR-2", "name": "Agricultural Income",
                "reason": "Agricultural income > ₹5,000"}

    return {"form": "ITR-1", "name": "Sahaj",
            "reason": "Salaried individual, income ≤ ₹50L"}


# ─── Audit Checks ─────────────────────────────────────────────────────────────

def run_audit_checks(tax_input: TaxInput) -> tuple[list[dict], list[dict]]:
    """
    Pre-filing compliance audit.
    Returns (errors, warnings).
    Errors = must fix before filing. Warnings = should review.
    """
    errors: list[dict] = []
    warnings: list[dict] = []

    # 80C limit
    if tax_input.section_80c > 150_000:
        errors.append({"id": "80c_limit", "section": "Deductions",
                        "msg": f"80C deductions exceed ₹1,50,000 limit (claimed: ₹{tax_input.section_80c:,.0f})",
                        "fix": "Reduce 80C claim to ₹1,50,000"})

    # HRA + 80GG conflict
    if (tax_input.hra > 0 or tax_input.hra_received > 0) and tax_input.section_80gg > 0:
        errors.append({"id": "hra_80gg", "section": "Deductions",
                        "msg": "Cannot claim both HRA exemption (Sec 10(13A)) and 80GG deduction",
                        "fix": "Claim only one — HRA if employer provides it, else 80GG"})

    # 80EE + 80EEA both claimed (mutually exclusive)
    if tax_input.section_80ee > 0 and tax_input.section_80eea > 0:
        errors.append({"id": "80ee_80eea", "section": "Deductions",
                        "msg": "80EE and 80EEA cannot both be claimed — they are mutually exclusive",
                        "fix": "Claim only 80EEA (higher limit ₹1.5L) if loan was sanctioned Apr19-Mar22"})

    # Crypto loss
    crypto_val = float((tax_input.capital_gains_detail or {}).get("crypto_vda", 0))
    if crypto_val < 0:
        errors.append({"id": "crypto_loss", "section": "Capital Gains",
                       "msg": "Crypto/VDA losses (Sec 115BBH) cannot be set off against any income or carried forward",
                       "fix": "Remove crypto loss from set-off; report gross VDA income only"})

    # ITR form vs income type mismatch
    cg_detail = tax_input.capital_gains_detail or {}
    if float(cg_detail.get("crypto_vda", 0)) > 0 and tax_input.entity_type == "individual":
        itr = determine_itr_form(tax_input)
        if itr["form"] == "ITR-1":
            errors.append({"id": "crypto_itr1", "section": "Filing",
                           "msg": "Crypto income requires ITR-2 or higher — ITR-1 cannot be filed",
                           "fix": "Switch to ITR-2"})

    # Capital gains consistency
    declared_cg = tax_input.capital_gains
    if cg_detail:
        computed_cg = sum(float(v) for v in cg_detail.values() if float(v) > 0)
        if computed_cg > 0 and abs(computed_cg - declared_cg) > 10:
            errors.append({"id": "cg_mismatch", "section": "Capital Gains",
                           "msg": f"CG schedule total ₹{computed_cg:,.0f} ≠ income head ₹{declared_cg:,.0f}",
                           "fix": "Sync the capital gains income head with the schedule total"})

    # Advance tax
    gross = (tax_input.salary + tax_input.business_income
             + tax_input.other_income + tax_input.interest_income)
    total_adv = (tax_input.advance_tax_q1 + tax_input.advance_tax_q2
                 + tax_input.advance_tax_q3 + tax_input.advance_tax_q4) or tax_input.advance_tax_paid
    if gross > 1_000_000 and total_adv == 0:
        warnings.append({"id": "advance_tax", "section": "Compliance",
                          "msg": "Income > ₹10L — advance tax liability likely (Sec 234B/234C)",
                          "fix": "Pay advance tax or expect interest penalty; check quarterly installments"})

    # Missing interest
    if tax_input.interest_income == 0:
        warnings.append({"id": "interest_missing", "section": "Income",
                          "msg": "No savings/FD interest declared — verify with bank statements and AIS",
                          "fix": "Check AIS on incometax.gov.in for TDS entries on interest"})

    # 80D missing
    if tax_input.section_80d == 0 and tax_input.section_80d_preventive == 0:
        warnings.append({"id": "80d_missing", "section": "Deductions",
                          "msg": "No health insurance premium declared — up to ₹25,000 deduction available",
                          "fix": "Enter health insurance premiums under 80D"})

    # Large cash deposits
    # (Forensics layer does this against actual transactions — placeholder)

    # Late filing flag
    today_m = date.today().month
    if today_m > 7:  # After July
        warnings.append({"id": "late_filing", "section": "Compliance",
                          "msg": "Filing after July 31 — late fee u/s 234F (₹5,000 or ₹1,000 if income ≤ ₹5L)",
                          "fix": "File immediately to avoid further interest"})

    return errors, warnings


# ─── Advance Tax Schedule ──────────────────────────────────────────────────────

def compute_advance_tax_schedule(total_tax: float) -> list[dict]:
    """Compute the 4 advance tax installments with due dates and amounts."""
    tds_net = total_tax  # caller should subtract TDS before passing
    schedule = [
        {"installment": "1st", "due_date": "June 15", "cumulative_pct": 15,
         "incremental_pct": 15},
        {"installment": "2nd", "due_date": "September 15", "cumulative_pct": 45,
         "incremental_pct": 30},
        {"installment": "3rd", "due_date": "December 15", "cumulative_pct": 75,
         "incremental_pct": 30},
        {"installment": "4th", "due_date": "March 15", "cumulative_pct": 100,
         "incremental_pct": 25},
    ]
    for item in schedule:
        item["cumulative_amount"] = round(tds_net * item["cumulative_pct"] / 100, 2)
        item["installment_amount"] = round(tds_net * item["incremental_pct"] / 100, 2)
    return schedule


# ─── Recommendation Engine ────────────────────────────────────────────────────

def generate_recommendations(
    tax_input: TaxInput,
    old: TaxBreakdown,
    new: TaxBreakdown,
) -> list[dict]:
    """Generate personalised, ranked tax-saving tips."""
    tips: list[dict] = []
    limits = DEDUCTION_LIMITS

    # Determine marginal rate for savings estimate
    marginal = _get_marginal_rate(old.taxable_income, old.surcharge_rate)

    def _tip(priority, title, desc, saving, section=""):
        tips.append({"priority": priority, "title": title, "desc": desc,
                      "potential_saving": round(saving, 2), "section": section})

    # 80C
    remaining_80c = max(0, limits["section_80c"] - tax_input.section_80c)
    if remaining_80c > 0:
        _tip("high",
             f"Invest ₹{remaining_80c:,.0f} more under 80C",
             f"PPF/ELSS/LIC/NSC/5yr FD — saves ₹{remaining_80c * marginal:,.0f} in old regime",
             remaining_80c * marginal, "80C")

    # 80CCD(1B)
    remaining_nps = max(0, limits["section_80ccd_1b"] - tax_input.nps_80ccd)
    if remaining_nps > 0:
        _tip("high",
             f"Add ₹{remaining_nps:,.0f} to NPS (80CCD(1B))",
             f"Over and above 80C limit — saves ₹{remaining_nps * marginal:,.0f}",
             remaining_nps * marginal, "80CCD(1B)")

    # 80CCD(2) — both regimes!
    if tax_input.basic_salary > 0:
        max_emp_nps = tax_input.basic_salary * 0.10
        remaining_emp_nps = max(0, max_emp_nps - tax_input.employer_nps)
        if remaining_emp_nps > 0:
            _tip("critical",
                 f"Ask HR to redirect ₹{remaining_emp_nps:,.0f} to Employer NPS (80CCD(2))",
                 "Works in BOTH regimes — saves without any investment limit",
                 remaining_emp_nps * marginal, "80CCD(2)")

    # 80D self
    age_limit_self = limits["section_80d_self_senior"] if tax_input.age >= 60 else limits["section_80d_self"]
    gap_80d = max(0, age_limit_self - tax_input.section_80d)
    if tax_input.section_80d == 0:
        _tip("critical",
             "Get Health Insurance → save up to ₹25,000 (80D)",
             "No health insurance claimed. Self + family premium deductible.",
             gap_80d * marginal, "80D")
    elif gap_80d > 0:
        _tip("medium",
             f"₹{gap_80d:,.0f} unused 80D headroom",
             "Increase health insurance cover or add parents",
             gap_80d * marginal, "80D")

    # 80D parents
    parent_limit = limits["section_80d_parents_senior"] if tax_input.parents_are_senior else limits["section_80d_parents"]
    if tax_input.section_80d_parents == 0 and tax_input.section_80d > 0:
        _tip("high",
             f"Parents' Health Insurance → extra ₹{parent_limit:,.0f} deduction (80D)",
             "₹50K if parents are senior citizens (60+)",
             parent_limit * marginal, "80D")

    # Preventive health check-up
    if tax_input.section_80d_preventive == 0:
        _tip("low",
             "Preventive health check-up → ₹5,000 deduction (cash allowed)",
             "Book a full-body check-up (Thyrocare/Redcliffe) — only section allowing cash",
             5_000 * marginal, "80D Preventive")

    # 80E — education loan
    if tax_input.section_80e == 0:
        _tip("low",
             "Education loan interest fully deductible (80E)",
             "If you or spouse/child have education loan — full interest deductible for 8 years",
             0, "80E")

    # 80EEB — EV loan
    if tax_input.section_80eeb == 0:
        _tip("low",
             "Electric vehicle loan → ₹1.5L interest deduction (80EEB)",
             "Consider EV for next vehicle — saves up to ₹45K tax at 30% bracket",
             150_000 * marginal, "80EEB")

    # HRA
    if tax_input.rent_paid > 0 and tax_input.hra_received > 0 and tax_input.hra == 0:
        hra_exempt = compute_hra_exemption(
            tax_input.basic_salary or tax_input.salary * 0.40,
            tax_input.hra_received,
            tax_input.rent_paid,
            tax_input.is_metro,
        )
        if hra_exempt > 0:
            _tip("high",
                 f"Claim HRA exemption of ₹{hra_exempt:,.0f}",
                 "Submit rent receipts + landlord PAN (if rent > ₹1L/year) to employer",
                 hra_exempt * marginal, "HRA")

    # Regime switch
    regime_diff = abs(old.total_tax - new.total_tax)
    if regime_diff > 1_000:
        better = "Old" if old.total_tax < new.total_tax else "New"
        _tip("high",
             f"Switch to {better} Regime → save ₹{regime_diff:,.0f}",
             f"The {better} regime is ₹{regime_diff:,.0f} cheaper with your current deductions",
             regime_diff, "Regime")

    # Tax-loss harvesting
    if any(float((tax_input.capital_gains_detail or {}).get(k, 0)) > 0
           for k in ("listed_equity_stcg", "listed_equity_ltcg", "equity_mf_stcg", "equity_mf_ltcg")):
        _tip("medium",
             "Consider tax-loss harvesting before March 31",
             "Review portfolio for unrealised losses — STCL offsets STCG and LTCG",
             0, "Capital Gains")

    # Sort: critical → high → medium → low
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    tips.sort(key=lambda t: (order.get(t["priority"], 3), -t["potential_saving"]))
    return tips


# ─── Helper: Build TaxInput from JSONB data ───────────────────────────────────

def build_tax_input_from_itr_data(
    income_data: dict | None,
    deductions_data: dict | None,
    filing_details: dict | None,
    fy: str = CURRENT_FY,
) -> TaxInput:
    """
    Construct TaxInput from JSONB dicts stored in ITRSubmission / ITRData.
    Backward-compatible with old key names; new fields gracefully default to 0.
    """
    inc = income_data or {}
    ded = deductions_data or {}
    fil = filing_details or {}

    def f(v: Any) -> float:
        try:
            return float(v or 0)
        except (TypeError, ValueError):
            return 0.0

    def b(v: Any) -> bool:
        return bool(v)

    return TaxInput(
        # Income
        salary=f(inc.get("salary")),
        house_property=f(inc.get("houseProperty")),
        business_income=f(inc.get("businessIncome")),
        capital_gains=f(inc.get("capitalGains")),
        other_income=f(inc.get("otherIncome")),
        interest_income=f(inc.get("interestIncome")),
        agricultural_income=f(inc.get("agriculturalIncome")),
        family_pension=f(inc.get("familyPension")),
        lottery_income=f(inc.get("lotteryIncome")),
        dividend_income=f(inc.get("dividendIncome")),

        # Salary components
        salary_components={k: f(v) for k, v in (inc.get("salary_components") or {}).items()},

        # HRA detailed
        basic_salary=f(inc.get("basic_salary")),
        hra_received=f(inc.get("hra_received")),
        rent_paid=f(inc.get("rent_paid") or ded.get("rentPaid")),

        # House property
        properties=inc.get("properties") or [],
        pre_construction_interest=f(inc.get("preConstructionInterest")),
        pre_construction_year=int(inc.get("preConstructionYear") or 0),

        # CG
        capital_gains_detail={k: f(v) for k, v in (inc.get("capital_gains_detail") or {}).items()},

        # Deductions — 80C
        section_80c=f(ded.get("section80C")),
        nps_80ccd=f(ded.get("nps80CCD")),
        employer_nps=f(ded.get("employer_nps")),

        # 80D
        section_80d=f(ded.get("section80D")),
        section_80d_preventive=f(ded.get("section80D_preventive")),
        section_80d_parents=f(ded.get("section80D_parents")),
        section_80d_parents_preventive=f(ded.get("section80D_parents_preventive")),

        # 80DD / 80DDB
        section_80dd=f(ded.get("section80DD")),
        section_80dd_severity=ded.get("section80DD_severity", "normal"),
        section_80ddb=f(ded.get("section80DDB")),

        # 80E through 80EEB
        section_80e=f(ded.get("section80E")),
        section_80ee=f(ded.get("section80EE")),
        section_80eea=f(ded.get("section80EEA")),
        section_80eea_eligible=b(ded.get("section80EEA_eligible")),
        section_80eeb=f(ded.get("section80EEB")),

        # 80G
        section_80g=f(ded.get("section80G")),
        section_80g_100pct=f(ded.get("section80G_100pct")),
        section_80g_50pct=f(ded.get("section80G_50pct")),
        section_80g_capped=f(ded.get("section80G_capped")),
        section_80gga=f(ded.get("section80GGA")),
        section_80ggc=f(ded.get("section80GGC")),

        # 80GG / 80TTA / 80U
        section_80gg=f(ded.get("section80GG")),
        section_80tta=f(ded.get("section80TTA")),
        section_80u=f(ded.get("section80U")),
        section_80u_severity=ded.get("section80U_severity", "normal"),

        # Home loan / HRA
        home_loan_interest=f(ded.get("homeLoanInterest")),
        hra=f(ded.get("hra")),
        lta_claimed=f(ded.get("ltaClaimed")),

        # Profile
        age=int(fil.get("age") or inc.get("age") or 30),
        is_presumptive=b(inc.get("isPresumptive") or fil.get("isPresumptive")),
        business_type=inc.get("businessType", "44ADA"),
        business_turnover=f(inc.get("businessTurnover")),
        profession_receipts=f(inc.get("professionReceipts")),
        is_metro=b(fil.get("isMetro") or inc.get("isMetro")),
        parents_are_senior=b(fil.get("parentsAreSenior")),
        is_nri=b(fil.get("isNRI")),
        has_foreign_assets=b(fil.get("foreignAssets")),
        is_director=b(fil.get("isDirector")),
        has_unlisted_equity=b(fil.get("hasUnlistedEquity")),
        entity_type=fil.get("entityType", "individual"),

        # Filing
        advance_tax_paid=f(fil.get("advanceTaxPaid")),
        advance_tax_q1=f(fil.get("advanceTaxQ1")),
        advance_tax_q2=f(fil.get("advanceTaxQ2")),
        advance_tax_q3=f(fil.get("advanceTaxQ3")),
        advance_tax_q4=f(fil.get("advanceTaxQ4")),
        tds_deducted=f(fil.get("tdsDeducted")),
        fy=fy if fy in NEW_REGIME_SLABS_BY_YEAR else CURRENT_FY,
    )
