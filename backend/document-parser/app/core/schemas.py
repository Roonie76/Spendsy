from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    FORM_16 = "form_16"
    FORM_16A = "form_16a"
    BROKER_STATEMENT = "broker_statement"
    BANK_STATEMENT = "bank_statement"
    AIS = "ais"


class VerificationStatus(str, Enum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


# ── Extracted fields ──────────────────────────────────────────────────────────

class Form16Data(BaseModel):
    """Structured data extracted from Form 16 (Part A + Part B)."""

    # Identity
    employee_name: Optional[str] = None
    employee_pan: Optional[str] = None
    employer_name: Optional[str] = None
    employer_tan: Optional[str] = None
    employer_pan: Optional[str] = None
    assessment_year: Optional[str] = None          # e.g. "2026-27"
    financial_year: Optional[str] = None           # e.g. "2025-26"

    # Salary (Part B)
    gross_salary: Optional[float] = None
    basic_salary: Optional[float] = None
    hra_received: Optional[float] = None
    special_allowance: Optional[float] = None
    other_allowances: Optional[float] = None
    perquisites: Optional[float] = None

    # Exemptions (Part B)
    hra_exemption: Optional[float] = None
    lta_exemption: Optional[float] = None
    standard_deduction: Optional[float] = None     # should be 75000 for FY25-26

    # Deductions claimed via employer
    deduction_80c: Optional[float] = None
    deduction_80d: Optional[float] = None
    deduction_nps_80ccd: Optional[float] = None
    deduction_employer_nps: Optional[float] = None
    home_loan_interest: Optional[float] = None

    # TDS (Part A)
    tds_deducted: Optional[float] = None
    tds_deposited: Optional[float] = None          # from 26AS cross-ref
    net_taxable_salary: Optional[float] = None

    # Metadata
    certificate_number: Optional[str] = None
    pdf_creator: Optional[str] = None             # payroll software signature
    raw_text_snippet: Optional[str] = None        # first 200 chars for audit


class BrokerStatementData(BaseModel):
    """Capital gains extracted from broker statement."""

    broker_name: Optional[str] = None
    pan: Optional[str] = None
    financial_year: Optional[str] = None

    stcg_equity: Optional[float] = None           # taxed @ 20%
    ltcg_equity: Optional[float] = None           # taxed @ 12.5% above 1.25L
    stcg_debt: Optional[float] = None             # slab rate
    ltcg_debt: Optional[float] = None             # 12.5%
    tds_on_gains: Optional[float] = None


class BankStatementData(BaseModel):
    """Interest income extracted from bank statement."""

    bank_name: Optional[str] = None
    account_number_masked: Optional[str] = None
    ifsc: Optional[str] = None
    account_type: Optional[str] = None

    savings_interest: Optional[float] = None
    fd_interest: Optional[float] = None
    rd_interest: Optional[float] = None


# ── Verification ──────────────────────────────────────────────────────────────

class VerificationCheck(BaseModel):
    name: str
    status: VerificationStatus
    message: str
    field: Optional[str] = None                   # which form field this relates to
    expected: Optional[str] = None
    found: Optional[str] = None


class VerificationResult(BaseModel):
    overall: VerificationStatus
    checks: list[VerificationCheck]
    trust_score: int = Field(..., ge=0, le=100)   # 0-100


# ── API response ──────────────────────────────────────────────────────────────

class ParseResponse(BaseModel):
    document_type: DocumentType
    document_hash: str                            # SHA-256 of uploaded bytes
    page_count: int
    extracted: Form16Data | BrokerStatementData | BankStatementData
    verification: VerificationResult
    autofill: dict                                # ready-to-use form field map
    warnings: list[str] = []


class AISCrossRefRequest(BaseModel):
    """Request to cross-reference extracted data against AIS."""
    pan: str
    assessment_year: str
    form16_tds: Optional[float] = None
    form16_employer_tan: Optional[str] = None
    reported_interest: Optional[float] = None
    reported_capital_gains: Optional[float] = None
