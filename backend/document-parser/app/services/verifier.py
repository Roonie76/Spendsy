"""
Document verification engine.

Runs layered checks on extracted Form 16 / broker statement data:
  Layer 1 — Structural / format checks (no external call needed)
  Layer 2 — Cross-reference against AIS / 26AS (requires user's AIS data)
  Layer 3 — Identity binding (PAN in doc vs logged-in user)
  Layer 4 — Reasonableness / anomaly checks

Returns a VerificationResult with per-check status + overall trust score.
"""
from __future__ import annotations

import re
import logging
from typing import Optional

from app.core.schemas import (
    BrokerStatementData,
    Form16Data,
    VerificationCheck,
    VerificationResult,
    VerificationStatus,
)

logger = logging.getLogger("doc_parser.verifier")

# ── Regex patterns ────────────────────────────────────────────────────────────
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
TAN_RE = re.compile(r"^[A-Z]{4}[0-9]{5}[A-Z]$")
AY_RE = re.compile(r"^\d{4}-\d{2}$")   # e.g. 2026-27

EXPECTED_AY = "2026-27"
EXPECTED_STD_DEDUCTION = 75000.0

# Payroll software signatures that appear in legit Form 16 PDF metadata
KNOWN_PAYROLL_CREATORS = [
    "greythr", "keka", "darwinbox", "sumhr", "zoho payroll",
    "sap", "oracle hrms", "myob", "saral tds", "gen tds",
    "computax", "winman", "cleartds", "traces",              # TRACES portal itself
]

# ── Scoring weights ───────────────────────────────────────────────────────────
# Each check contributes to trust_score. Failures deduct points.
WEIGHTS = {
    "pan_format":           10,
    "tan_format":           10,
    "ay_match":             15,
    "std_deduction":         5,
    "pdf_creator":           5,
    "pan_identity_match":   20,   # biggest single check
    "tds_26as_match":       20,   # AIS cross-ref
    "reasonableness":       10,
    "round_number":          5,
}


def _check(
    name: str,
    status: VerificationStatus,
    message: str,
    field: str | None = None,
    expected: str | None = None,
    found: str | None = None,
) -> VerificationCheck:
    return VerificationCheck(
        name=name,
        status=status,
        message=message,
        field=field,
        expected=expected,
        found=found,
    )


def _ok(name: str, msg: str, field: str | None = None) -> VerificationCheck:
    return _check(name, VerificationStatus.PASSED, msg, field)

def _warn(name: str, msg: str, field: str | None = None, expected: str | None = None, found: str | None = None) -> VerificationCheck:
    return _check(name, VerificationStatus.WARNING, msg, field, expected, found)

def _fail(name: str, msg: str, field: str | None = None, expected: str | None = None, found: str | None = None) -> VerificationCheck:
    return _check(name, VerificationStatus.FAILED, msg, field, expected, found)


# ── Layer 1: Structural checks ────────────────────────────────────────────────

def check_pan_format(pan: Optional[str]) -> VerificationCheck:
    if not pan:
        return _warn("pan_format", "Employee PAN not found in document.", "employee_pan")
    if PAN_RE.match(pan.upper()):
        return _ok("pan_format", f"PAN format valid: {pan}")
    return _fail("pan_format", f"Invalid PAN format: '{pan}'. Expected 5 letters + 4 digits + 1 letter.", "employee_pan", "ABCDE1234F", pan)


def check_tan_format(tan: Optional[str]) -> VerificationCheck:
    if not tan:
        return _warn("tan_format", "Employer TAN not found in document.", "employer_tan")
    if TAN_RE.match(tan.upper()):
        return _ok("tan_format", f"Employer TAN format valid: {tan}")
    return _fail("tan_format", f"Invalid TAN format: '{tan}'. Expected 4 letters + 5 digits + 1 letter.", "employer_tan", "BLRX12345A", tan)


def check_assessment_year(ay: Optional[str]) -> VerificationCheck:
    if not ay:
        return _warn("ay_match", "Assessment year not found in document.", "assessment_year")
    if not AY_RE.match(ay):
        return _fail("ay_match", f"Assessment year format invalid: '{ay}'.", "assessment_year", EXPECTED_AY, ay)
    if ay != EXPECTED_AY:
        return _fail(
            "ay_match",
            f"Document is for AY {ay}, but you are filing for AY {EXPECTED_AY}. Wrong year document.",
            "assessment_year",
            EXPECTED_AY,
            ay,
        )
    return _ok("ay_match", f"Assessment year matches: {ay}")


def check_standard_deduction(std_ded: Optional[float]) -> VerificationCheck:
    if std_ded is None:
        return _warn("std_deduction", "Standard deduction not found. Will default to ₹75,000.", "standard_deduction")
    if abs(std_ded - EXPECTED_STD_DEDUCTION) < 1:
        return _ok("std_deduction", "Standard deduction ₹75,000 confirmed.")
    return _warn(
        "std_deduction",
        f"Standard deduction is ₹{std_ded:,.0f}, expected ₹75,000 for FY 2025-26. Verify with employer.",
        "standard_deduction",
        "75000",
        str(std_ded),
    )


def check_pdf_creator(creator: Optional[str]) -> VerificationCheck:
    if not creator:
        return _warn("pdf_creator", "PDF creator metadata missing — could be a scanned document or manually created PDF.")
    creator_lower = creator.lower()
    for known in KNOWN_PAYROLL_CREATORS:
        if known in creator_lower:
            return _ok("pdf_creator", f"PDF generated by known payroll software: '{creator}'.")
    return _warn(
        "pdf_creator",
        f"PDF creator '{creator}' is not a recognised payroll platform. Manually created PDFs carry higher forgery risk.",
        found=creator,
    )


# ── Layer 2: AIS / 26AS cross-reference ──────────────────────────────────────

def check_tds_against_26as(
    form16_tds: Optional[float],
    ais_tds: Optional[float],
) -> VerificationCheck:
    """
    Compare TDS in Form 16 against what the employer deposited per 26AS.
    ais_tds is fetched from the user's 26AS (passed in from the API layer).
    If AIS data is not available, return a warning instead of failing.
    """
    if ais_tds is None:
        return _warn(
            "tds_26as_match",
            "AIS / 26AS data not provided. Cannot cross-verify TDS. Connect AIS import for stronger validation.",
        )
    if form16_tds is None:
        return _warn("tds_26as_match", "TDS amount not extracted from Form 16.", "tds_deducted")

    diff = abs(form16_tds - ais_tds)
    pct_diff = diff / max(ais_tds, 1) * 100

    if pct_diff < 1:   # within 1% — rounding differences are fine
        return _ok("tds_26as_match", f"TDS matches 26AS: ₹{form16_tds:,.0f} vs ₹{ais_tds:,.0f} in 26AS.")
    if pct_diff < 5:
        return _warn(
            "tds_26as_match",
            f"Minor TDS discrepancy: Form 16 shows ₹{form16_tds:,.0f} but 26AS shows ₹{ais_tds:,.0f} ({pct_diff:.1f}% difference). Verify with employer.",
            "tds_deducted",
            f"₹{ais_tds:,.0f}",
            f"₹{form16_tds:,.0f}",
        )
    return _fail(
        "tds_26as_match",
        f"Significant TDS mismatch: Form 16 shows ₹{form16_tds:,.0f} but 26AS shows ₹{ais_tds:,.0f} ({pct_diff:.1f}% difference). "
        "The Form 16 may be forged or the employer has not deposited TDS. Do NOT file with this TDS amount.",
        "tds_deducted",
        f"₹{ais_tds:,.0f} (from 26AS)",
        f"₹{form16_tds:,.0f} (from Form 16)",
    )


# ── Layer 3: Identity binding ─────────────────────────────────────────────────

def check_pan_identity(doc_pan: Optional[str], user_pan: Optional[str]) -> VerificationCheck:
    if not user_pan:
        return _warn("pan_identity_match", "User PAN not available for identity check.")
    if not doc_pan:
        return _warn("pan_identity_match", "PAN not found in document — cannot verify identity.", "employee_pan")
    if doc_pan.upper() == user_pan.upper():
        return _ok("pan_identity_match", f"Document PAN matches your account PAN: {doc_pan}.")
    return _fail(
        "pan_identity_match",
        f"Document PAN ({doc_pan}) does NOT match your account PAN ({user_pan}). "
        "This Form 16 belongs to a different taxpayer.",
        "employee_pan",
        user_pan,
        doc_pan,
    )


# ── Layer 4: Reasonableness checks ───────────────────────────────────────────

def check_reasonableness(data: Form16Data) -> VerificationCheck:
    issues = []

    # Deductions vs gross salary
    if data.gross_salary and data.gross_salary > 0:
        total_80c = data.deduction_80c or 0
        if total_80c > data.gross_salary * 0.70:
            issues.append(f"80C deduction (₹{total_80c:,.0f}) exceeds 70% of gross salary — unusually high.")

        # HRA exemption can't exceed HRA received
        if data.hra_exemption and data.hra_received:
            if data.hra_exemption > data.hra_received:
                issues.append(f"HRA exemption (₹{data.hra_exemption:,.0f}) exceeds HRA received (₹{data.hra_received:,.0f}) — impossible.")

        # TDS sanity: can't be more than gross salary
        if data.tds_deducted and data.tds_deducted > data.gross_salary:
            issues.append(f"TDS (₹{data.tds_deducted:,.0f}) exceeds gross salary (₹{data.gross_salary:,.0f}) — impossible.")

        # Net taxable salary should be less than gross
        if data.net_taxable_salary and data.net_taxable_salary > data.gross_salary * 1.05:
            issues.append("Net taxable salary is higher than gross salary — check deductions/exemptions.")

    if issues:
        return _warn(
            "reasonableness",
            "Reasonableness check flagged: " + " | ".join(issues),
        )
    return _ok("reasonableness", "Income and deduction figures appear reasonable.")


def check_round_numbers(data: Form16Data) -> VerificationCheck:
    """
    Forgers tend to use perfectly round numbers for every field simultaneously.
    Real payroll rarely produces all-round figures.
    """
    numeric_fields = [
        data.gross_salary, data.basic_salary, data.hra_received,
        data.tds_deducted, data.deduction_80c, data.deduction_80d,
    ]
    non_null = [v for v in numeric_fields if v is not None and v > 0]
    if not non_null:
        return _ok("round_number", "Insufficient numeric fields to check.")

    round_count = sum(1 for v in non_null if v % 1000 == 0)
    round_ratio = round_count / len(non_null)

    if round_ratio >= 0.85 and len(non_null) >= 4:
        return _warn(
            "round_number",
            f"{round_count}/{len(non_null)} monetary fields are exact multiples of ₹1,000. "
            "Genuine payroll documents rarely have all-round figures. Please verify.",
        )
    return _ok("round_number", "Numeric values show realistic payroll variation.")


# ── Main verifier ─────────────────────────────────────────────────────────────

def verify_form16(
    data: Form16Data,
    pdf_creator: Optional[str] = None,
    user_pan: Optional[str] = None,
    ais_tds: Optional[float] = None,
) -> VerificationResult:
    """Run all verification layers and return a scored result."""

    checks: list[VerificationCheck] = [
        # Layer 1
        check_pan_format(data.employee_pan),
        check_tan_format(data.employer_tan),
        check_assessment_year(data.assessment_year),
        check_standard_deduction(data.standard_deduction),
        check_pdf_creator(pdf_creator),
        # Layer 2
        check_tds_against_26as(data.tds_deducted, ais_tds),
        # Layer 3
        check_pan_identity(data.employee_pan, user_pan),
        # Layer 4
        check_reasonableness(data),
        check_round_numbers(data),
    ]

    # Score computation
    score = 100
    for check in checks:
        weight = WEIGHTS.get(check.name, 5)
        if check.status == VerificationStatus.FAILED:
            score -= weight
        elif check.status == VerificationStatus.WARNING:
            score -= weight // 2
    score = max(0, score)

    # Overall status
    has_failure = any(c.status == VerificationStatus.FAILED for c in checks)
    has_warning = any(c.status == VerificationStatus.WARNING for c in checks)
    if has_failure:
        overall = VerificationStatus.FAILED
    elif has_warning:
        overall = VerificationStatus.WARNING
    else:
        overall = VerificationStatus.PASSED

    return VerificationResult(overall=overall, checks=checks, trust_score=score)


def verify_broker_statement(
    data: BrokerStatementData,
    user_pan: Optional[str] = None,
    ais_capital_gains: Optional[float] = None,
) -> VerificationResult:
    checks: list[VerificationCheck] = []

    # PAN check
    if data.pan and user_pan:
        checks.append(check_pan_identity(data.pan, user_pan))
    else:
        checks.append(_warn("pan_identity_match", "PAN not found in broker statement."))

    # FY check
    if data.financial_year and "2025-26" not in (data.financial_year or ""):
        checks.append(_fail("ay_match", f"Broker statement is for FY {data.financial_year}, not FY 2025-26.", "financial_year"))
    else:
        checks.append(_ok("ay_match", "Financial year matches FY 2025-26."))

    # AIS capital gains cross-reference
    total_cg = (data.stcg_equity or 0) + (data.ltcg_equity or 0) + (data.stcg_debt or 0) + (data.ltcg_debt or 0)
    if ais_capital_gains is not None:
        diff_pct = abs(total_cg - ais_capital_gains) / max(ais_capital_gains, 1) * 100
        if diff_pct < 5:
            checks.append(_ok("tds_26as_match", f"Capital gains (₹{total_cg:,.0f}) matches AIS data."))
        else:
            checks.append(_warn(
                "tds_26as_match",
                f"Capital gains in statement (₹{total_cg:,.0f}) differs from AIS (₹{ais_capital_gains:,.0f}) by {diff_pct:.1f}%.",
                expected=f"₹{ais_capital_gains:,.0f}",
                found=f"₹{total_cg:,.0f}",
            ))
    else:
        checks.append(_warn("tds_26as_match", "AIS capital gains data not available for cross-reference."))

    score = 100
    for c in checks:
        if c.status == VerificationStatus.FAILED:
            score -= 30
        elif c.status == VerificationStatus.WARNING:
            score -= 10
    score = max(0, score)

    has_failure = any(c.status == VerificationStatus.FAILED for c in checks)
    has_warning = any(c.status == VerificationStatus.WARNING for c in checks)
    overall = (
        VerificationStatus.FAILED if has_failure
        else VerificationStatus.WARNING if has_warning
        else VerificationStatus.PASSED
    )
    return VerificationResult(overall=overall, checks=checks, trust_score=score)
