"""
investment_parser.py — Parser for NPS statements, PPF passbooks,
ELSS statements, rent receipts, home-loan interest certificates,
and health insurance premium receipts.

Each document type returns its own result dataclass.
The dispatcher `parse_investment_doc(bytes, doc_type)` routes correctly.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger("finance.parser.investment")
PARSER_VERSION = "1.0.0"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _open_pdf(content: bytes):
    import pdfplumber
    return pdfplumber.open(io.BytesIO(content))


def _extract_all_text(content: bytes) -> tuple[str, int, bool]:
    """Returns (full_text, page_count, ocr_used)."""
    import pdfplumber
    parts: list[str] = []
    ocr_used = False
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            n = len(pdf.pages)
            for page in pdf.pages:
                pg = page.extract_text() or ""
                if len(page.extract_words()) < 20:
                    try:
                        import pytesseract
                        img = page.to_image(resolution=200).original
                        pg = pytesseract.image_to_string(img, config="--psm 6")
                        ocr_used = True
                    except Exception:
                        pass
                parts.append(pg)
        return "\n".join(parts), n, ocr_used
    except Exception as e:
        raise ValueError(f"Cannot read PDF: {e}") from e


def _parse_num(s: str) -> float:
    if not s:
        return 0.0
    return float(s.replace(",", "").strip())


def _first(pattern: re.Pattern, text: str) -> Optional[float]:
    m = pattern.search(text)
    return _parse_num(m.group(1)) if m else None


def _first_str(pattern: re.Pattern, text: str) -> Optional[str]:
    m = pattern.search(text)
    return m.group(1).strip() if m else None


# ─────────────────────────────────────────────────────────────────────────────
# NPS Statement
# ─────────────────────────────────────────────────────────────────────────────

_NPS_PRAN = re.compile(r"PRAN\s*[:\-]?\s*(\d{12})", re.I)
_NPS_NAME = re.compile(r"(?:Subscriber\s+Name|Name)\s*[:\-]?\s*([A-Z][A-Z\s\.]{2,50})", re.I)
_NPS_FY   = re.compile(r"(?:Financial\s+Year|FY)\s*[:\-]?\s*(\d{4}[\-–]\d{2,4})", re.I)
_NPS_SELF_CONTRIB = re.compile(
    r"(?:Employee|Subscriber|Self)\s+Contribution[^\d]*([\d,]+(?:\.\d{1,2})?)", re.I)
_NPS_EMP_CONTRIB  = re.compile(
    r"(?:Employer|Corporate)\s+Contribution[^\d]*([\d,]+(?:\.\d{1,2})?)", re.I)
_NPS_TOTAL_CORPUS = re.compile(
    r"(?:Total|Closing|Net\s+Asset\s+Value)[^\d]*([\d,]+(?:\.\d{1,2})?)", re.I)


@dataclass
class NPSParseResult:
    pran: Optional[str] = None
    subscriber_name: Optional[str] = None
    fy: Optional[str] = None
    self_contribution: float = 0.0       # 80CCD(1B) eligible
    employer_contribution: float = 0.0   # 80CCD(2) eligible
    corpus_value: float = 0.0
    confidence_score: float = 0.0
    field_confidence: dict[str, float] = field(default_factory=dict)
    ocr_used: bool = False
    page_count: int = 0


def parse_nps_statement(content: bytes) -> NPSParseResult:
    full_text, n, ocr = _extract_all_text(content)
    r = NPSParseResult(ocr_used=ocr, page_count=n)
    conf: dict[str, float] = {}

    if not re.search(r"NPS|National\s+Pension|PRAN|CRA", full_text, re.I):
        raise ValueError("Document does not appear to be an NPS statement")

    r.pran = _first_str(_NPS_PRAN, full_text)
    if r.pran: conf["pran"] = 95.0
    r.subscriber_name = _first_str(_NPS_NAME, full_text)
    if r.subscriber_name: conf["name"] = 80.0
    r.fy = _first_str(_NPS_FY, full_text)
    if r.fy: conf["fy"] = 90.0

    r.self_contribution = _first(_NPS_SELF_CONTRIB, full_text) or 0.0
    if r.self_contribution: conf["self_contribution"] = 85.0
    r.employer_contribution = _first(_NPS_EMP_CONTRIB, full_text) or 0.0
    if r.employer_contribution: conf["employer_contribution"] = 85.0
    r.corpus_value = _first(_NPS_TOTAL_CORPUS, full_text) or 0.0

    filled = sum(1 for v in conf.values() if v > 0)
    r.confidence_score = round(filled / max(len(conf), 1) * 100, 1)
    r.field_confidence = conf
    return r


# ─────────────────────────────────────────────────────────────────────────────
# PPF Passbook / Statement
# ─────────────────────────────────────────────────────────────────────────────

_PPF_ACCT = re.compile(r"Account\s+(?:No\.?|Number)\s*[:\-]?\s*(PPF/\w+|\d{8,20})", re.I)
_PPF_FY_DEP = re.compile(
    r"(?:Total\s+)?(?:FY\s+)?Deposits?\s*(?:in\s+(?:FY|Financial\s+Year))?\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_PPF_BALANCE = re.compile(r"(?:Closing|Balance)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_PPF_INTEREST = re.compile(r"Interest\s+(?:Credited|Earned)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)


@dataclass
class PPFParseResult:
    account_no: Optional[str] = None
    fy_deposits: float = 0.0             # 80C eligible amount
    interest_credited: float = 0.0       # Tax-free
    closing_balance: float = 0.0
    confidence_score: float = 0.0
    field_confidence: dict[str, float] = field(default_factory=dict)
    ocr_used: bool = False
    page_count: int = 0


def parse_ppf_statement(content: bytes) -> PPFParseResult:
    full_text, n, ocr = _extract_all_text(content)
    r = PPFParseResult(ocr_used=ocr, page_count=n)
    conf: dict[str, float] = {}

    r.account_no = _first_str(_PPF_ACCT, full_text)
    if r.account_no: conf["account"] = 90.0
    r.fy_deposits = _first(_PPF_FY_DEP, full_text) or 0.0
    if r.fy_deposits: conf["fy_deposits"] = 80.0
    r.interest_credited = _first(_PPF_INTEREST, full_text) or 0.0
    r.closing_balance = _first(_PPF_BALANCE, full_text) or 0.0

    filled = sum(1 for v in conf.values() if v > 0)
    r.confidence_score = round(filled / max(len(conf), 1) * 100, 1)
    r.field_confidence = conf
    return r


# ─────────────────────────────────────────────────────────────────────────────
# ELSS / Mutual Fund investment statement
# ─────────────────────────────────────────────────────────────────────────────

_ELSS_TOTAL = re.compile(
    r"(?:Total\s+)?(?:ELSS|Tax\s+Saver|Tax\s+Saving)\s+"
    r"(?:Investment|Purchase|SIP)?\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_MF_TOTAL = re.compile(
    r"Total\s+(?:Purchase|Investment|SIP)\s*(?:Amount)?\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)


@dataclass
class ELSSParseResult:
    elss_invested: float = 0.0      # 80C eligible
    other_mf_invested: float = 0.0
    confidence_score: float = 0.0
    field_confidence: dict[str, float] = field(default_factory=dict)
    ocr_used: bool = False
    page_count: int = 0


def parse_elss_statement(content: bytes) -> ELSSParseResult:
    full_text, n, ocr = _extract_all_text(content)
    r = ELSSParseResult(ocr_used=ocr, page_count=n)
    conf: dict[str, float] = {}

    r.elss_invested = _first(_ELSS_TOTAL, full_text) or 0.0
    if r.elss_invested: conf["elss"] = 80.0
    r.other_mf_invested = _first(_MF_TOTAL, full_text) or 0.0

    filled = sum(1 for v in conf.values() if v > 0)
    r.confidence_score = round(filled / max(len(conf), 1) * 100, 1)
    r.field_confidence = conf
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Rent receipts
# ─────────────────────────────────────────────────────────────────────────────

_RENT_MONTHLY = re.compile(
    r"(?:Monthly\s+Rent|Rent\s+(?:per\s+month|per\s+Month))\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_RENT_ANNUAL = re.compile(
    r"(?:Annual\s+Rent|Yearly\s+Rent|Total\s+Rent\s+Paid)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_LANDLORD_PAN = re.compile(r"(?:Landlord|Owner)\s+PAN\s*[:\-]?\s*([A-Z]{5}\d{4}[A-Z])", re.I)
_RENTAL_ADDR  = re.compile(r"(?:Property|Rental)\s+Address\s*[:\-]?\s*(.{10,100}?)(?:\n|$)", re.I)


@dataclass
class RentReceiptParseResult:
    monthly_rent: float = 0.0
    annual_rent: float = 0.0        # for HRA / 80GG calc
    landlord_pan: Optional[str] = None
    rental_address: Optional[str] = None
    confidence_score: float = 0.0
    field_confidence: dict[str, float] = field(default_factory=dict)
    ocr_used: bool = False
    page_count: int = 0


def parse_rent_receipts(content: bytes) -> RentReceiptParseResult:
    full_text, n, ocr = _extract_all_text(content)
    r = RentReceiptParseResult(ocr_used=ocr, page_count=n)
    conf: dict[str, float] = {}

    r.monthly_rent = _first(_RENT_MONTHLY, full_text) or 0.0
    if r.monthly_rent: conf["monthly_rent"] = 85.0
    r.annual_rent = _first(_RENT_ANNUAL, full_text) or 0.0
    if r.annual_rent == 0.0 and r.monthly_rent > 0:
        r.annual_rent = r.monthly_rent * 12
        conf["annual_rent"] = 75.0
    elif r.annual_rent: conf["annual_rent"] = 85.0
    r.landlord_pan = _first_str(_LANDLORD_PAN, full_text)
    if r.landlord_pan: conf["landlord_pan"] = 95.0
    r.rental_address = _first_str(_RENTAL_ADDR, full_text)

    filled = sum(1 for v in conf.values() if v > 0)
    r.confidence_score = round(filled / max(len(conf), 1) * 100, 1)
    r.field_confidence = conf
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Home Loan Interest Certificate
# ─────────────────────────────────────────────────────────────────────────────

_HL_INTEREST = re.compile(
    r"(?:Interest\s+(?:Paid|Charged|Accrued)|Principal.*?Interest)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_HL_PRINCIPAL = re.compile(
    r"(?:Principal\s+(?:Paid|Repaid|Repayment))\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_HL_OUTSTANDING = re.compile(
    r"(?:Outstanding|Closing)\s+(?:Loan\s+)?Balance\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)
_HL_LOAN_ACCT = re.compile(r"Loan\s+(?:Account\s+)?(?:No\.?|Number)\s*[:\-]?\s*(\w{5,20})", re.I)
_HL_BANK_NAME = re.compile(r"(?:Bank|Lender|NBFC)\s+Name\s*[:\-]?\s*([A-Z][A-Za-z\s]{3,50})", re.I)


@dataclass
class HomeLoanCertParseResult:
    interest_paid: float = 0.0          # Sec 24(b) deduction
    principal_paid: float = 0.0         # 80C deduction
    outstanding_balance: float = 0.0
    loan_account_no: Optional[str] = None
    bank_name: Optional[str] = None
    confidence_score: float = 0.0
    field_confidence: dict[str, float] = field(default_factory=dict)
    ocr_used: bool = False
    page_count: int = 0


def parse_home_loan_certificate(content: bytes) -> HomeLoanCertParseResult:
    full_text, n, ocr = _extract_all_text(content)
    r = HomeLoanCertParseResult(ocr_used=ocr, page_count=n)
    conf: dict[str, float] = {}

    r.interest_paid = _first(_HL_INTEREST, full_text) or 0.0
    if r.interest_paid: conf["interest"] = 88.0
    r.principal_paid = _first(_HL_PRINCIPAL, full_text) or 0.0
    if r.principal_paid: conf["principal"] = 88.0
    r.outstanding_balance = _first(_HL_OUTSTANDING, full_text) or 0.0
    r.loan_account_no = _first_str(_HL_LOAN_ACCT, full_text)
    if r.loan_account_no: conf["loan_acct"] = 90.0
    r.bank_name = _first_str(_HL_BANK_NAME, full_text)

    filled = sum(1 for v in conf.values() if v > 0)
    r.confidence_score = round(filled / max(len(conf), 1) * 100, 1)
    r.field_confidence = conf
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Dispatcher
# ─────────────────────────────────────────────────────────────────────────────

DOC_TYPE_MAP = {
    "nps_statement":  parse_nps_statement,
    "ppf_passbook":   parse_ppf_statement,
    "elss_statement": parse_elss_statement,
    "rent_receipt":   parse_rent_receipts,
    "hl_certificate": parse_home_loan_certificate,
}


def parse_investment_doc(content: bytes, doc_type: str):
    """Route to correct parser by doc_type. Returns the appropriate result dataclass."""
    parser_fn = DOC_TYPE_MAP.get(doc_type)
    if not parser_fn:
        raise ValueError(f"Unknown investment doc_type: {doc_type!r}")
    return parser_fn(content)


def investment_to_itr_fields(result, doc_type: str) -> dict:
    """Map investment parse result → field dicts."""
    if doc_type == "nps_statement":
        return {
            "deductions_data": {
                "nps_self_80ccd1b":    result.self_contribution,
                "nps_employer_80ccd2": result.employer_contribution,
                "_source": "nps_statement",
            }
        }
    if doc_type == "ppf_passbook":
        return {
            "deductions_data": {
                "_ppf_amount": result.fy_deposits,
                "_source": "ppf_passbook",
            }
        }
    if doc_type == "elss_statement":
        return {
            "deductions_data": {
                "_elss_amount": result.elss_invested,
                "_source": "elss_statement",
            }
        }
    if doc_type == "rent_receipt":
        return {
            "income_data": {
                "rent_paid": result.annual_rent,
                "_landlord_pan": result.landlord_pan,
                "_source": "rent_receipt",
            }
        }
    if doc_type == "hl_certificate":
        return {
            "income_data": {
                "home_loan_interest": result.interest_paid,
                "_hl_principal": result.principal_paid,
                "_source": "hl_certificate",
            },
            "deductions_data": {
                "_hl_principal_80c": result.principal_paid,
                "_source": "hl_certificate",
            },
        }
    return {}
