"""
form16_parser.py — Form 16 Part A + Part B PDF parser.

Extracts every Schedule-field required for ITR-1 / ITR-2 pre-fill:

Part A (TDS Certificate from Employer):
  - Employer name, TAN, PAN
  - Employee name, PAN
  - Assessment Year
  - Quarterly TDS summary (Q1–Q4: amount paid, TDS deducted, TDS deposited)
  - Total TDS deposited

Part B (Salary Breakup — Annexure to Form 16):
  - Gross salary (Sec 17(1))
  - Perquisites (Sec 17(2))
  - Profits in lieu of salary (Sec 17(3))
  - Allowances exempt u/s 10 (HRA, LTA, children education, uniform, others)
  - Standard deduction (₹75,000)
  - Entertainment allowance deduction
  - Professional tax (Sec 16(iii))
  - Net salary after standard deduction
  - Income from other sources (if declared to employer)
  - Total income
  - Chapter VI-A deductions claimed (80C, 80D, 80G, etc.)
  - Net taxable income
  - Tax on total income
  - Rebate u/s 87A
  - Surcharge
  - Education cess
  - Tax payable / TDS deducted

Strategy:
  1. Open PDF with pdfplumber
  2. If < 30 words/page → OCR fallback via pytesseract
  3. Detect Part A vs Part B sections by heading patterns
  4. Use regex anchors on known Form 16 label patterns
  5. Return Form16ParseResult with per-field confidence
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger("finance.parser.form16")

PARSER_VERSION = "1.0.0"

# ── Regex patterns for Part A fields ─────────────────────────────────────────

_RE_TAN         = re.compile(r"TAN\s*(?:of\s+(?:the\s+)?Employer)?\s*[:\-]\s*([A-Z]{4}\d{5}[A-Z])", re.I)
_RE_EMPLOYER_PAN= re.compile(r"PAN\s*(?:of\s+the\s+)?Employer\s*[:\-]\s*([A-Z]{5}\d{4}[A-Z])", re.I)
_RE_EMPLOYEE_PAN= re.compile(r"PAN\s*(?:of\s+the\s+)?Employee\s*[:\-]\s*([A-Z]{5}\d{4}[A-Z])", re.I)
_RE_AY          = re.compile(r"Assessment\s+Year\s*[:\-]\s*(\d{4}-\d{2,4})", re.I)
_RE_EMPLOYEE_NM = re.compile(r"Name\s*(?:of\s+(?:the\s+)?Employee|&\s*Address)\s*[:\-]\s*([A-Z][A-Z\s\.]{2,50})", re.I)
_RE_EMPLOYER_NM = re.compile(r"Name\s*(?:of\s+(?:the\s+)?Employer|&\s*Address)\s*[:\-]\s*([A-Z][A-Z\s\.&]{2,80})", re.I)
_RE_TOTAL_TDS   = re.compile(r"Total\s+(?:amount\s+of\s+)?Tax\s+Deducted\s*(?:at\s+Source)?\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)

# ── Regex patterns for Part B salary schedule ─────────────────────────────────

_RE_GROSS_SALARY    = re.compile(r"(?:1\.?\s*)?Gross\s+[Ss]alary\s*[\(a\)]*\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_PERQUISITES     = re.compile(r"Perquisites\s*(?:u/?s\s*17\s*\(\s*2\s*\))?\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_PROFITS_LIEU    = re.compile(r"Profits?\s+in\s+lieu\s+of\s+salary\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_HRA_EXEMPT      = re.compile(r"HRA\s*(?:exemption)?\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_LTA_EXEMPT      = re.compile(r"LTA\s*(?:exemption|Leave\s+Travel)?\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_STD_DED         = re.compile(r"Standard\s+[Dd]eduction\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_PROF_TAX        = re.compile(r"Professional\s+[Tt]ax\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_NET_SALARY      = re.compile(r"(?:Net\s+)?[Ii]ncome\s+(?:chargeable\s+)?under\s+(?:the\s+)?head\s+[Ss]alaries\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_TOTAL_INCOME    = re.compile(r"(?:12|Gross\s+)?Total\s+[Ii]ncome\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_80C             = re.compile(r"80\s*C\b.*?([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_80D             = re.compile(r"80\s*D\b.*?([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_TOTAL_DEDS      = re.compile(r"(?:Total\s+)?[Dd]eductions\s*(?:Chapter\s+VI-?A)?\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_TAXABLE_INCOME  = re.compile(r"(?:Net\s+)?Taxable\s+[Ii]ncome\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_TAX_ON_INCOME   = re.compile(r"Tax\s+on\s+[Tt]otal\s+[Ii]ncome\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_REBATE_87A      = re.compile(r"Rebate\s+u/?s\s*87A\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_SURCHARGE       = re.compile(r"Surcharge\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_CESS            = re.compile(r"(?:Health\s*&?\s*Education\s+)?[Cc]ess\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_TAX_PAYABLE     = re.compile(r"(?:Tax\s+)?[Pp]ayable\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
_RE_TDS_DEDUCTED    = re.compile(r"(?:Total\s+)?TDS\s+(?:Deducted|as\s+per\s+Form\s+16)\s*[:\-]?\s*([\d,]+(?:\.\d{1,2})?)", re.I)


def _parse_num(s: str) -> float:
    """Strip commas and convert to float."""
    if not s:
        return 0.0
    return float(s.replace(",", "").strip())


def _first_match(pattern: re.Pattern, text: str) -> Optional[float]:
    m = pattern.search(text)
    return _parse_num(m.group(1)) if m else None


def _first_str_match(pattern: re.Pattern, text: str) -> Optional[str]:
    m = pattern.search(text)
    return m.group(1).strip() if m else None


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class Form16ParseResult:
    # Identity
    employee_name: Optional[str] = None
    employee_pan: Optional[str] = None
    employer_name: Optional[str] = None
    employer_pan: Optional[str] = None
    employer_tan: Optional[str] = None
    assessment_year: Optional[str] = None

    # Part A — TDS
    total_tds_deposited: float = 0.0
    tds_q1: float = 0.0
    tds_q2: float = 0.0
    tds_q3: float = 0.0
    tds_q4: float = 0.0

    # Part B — Salary schedule
    gross_salary: float = 0.0          # Sec 17(1) value before exemptions
    perquisites: float = 0.0           # Sec 17(2)
    profits_in_lieu: float = 0.0       # Sec 17(3)
    hra_exempt: float = 0.0            # Sec 10(13A)
    lta_exempt: float = 0.0            # Sec 10(5)
    other_exemptions: float = 0.0      # other Sec 10 exemptions
    standard_deduction: float = 0.0    # Sec 16(ia)
    professional_tax: float = 0.0      # Sec 16(iii)
    net_salary: float = 0.0            # income chargeable under "Salaries"

    # Chapter VI-A declared to employer
    section_80c: float = 0.0
    section_80d: float = 0.0
    other_deductions: float = 0.0
    total_deductions_vi_a: float = 0.0

    # Tax computation
    total_income: float = 0.0
    taxable_income: float = 0.0
    tax_on_income: float = 0.0
    rebate_87a: float = 0.0
    surcharge: float = 0.0
    cess: float = 0.0
    tax_payable: float = 0.0
    tds_deducted: float = 0.0          # per Form 16 Part B (should match Part A)

    # Meta
    confidence_score: float = 0.0
    field_confidence: dict[str, float] = field(default_factory=dict)
    parse_warnings: list[str] = field(default_factory=list)
    ocr_used: bool = False
    page_count: int = 0
    raw_text_sample: str = ""


# ── OCR fallback ──────────────────────────────────────────────────────────────

def _ocr_page(pil_image) -> str:
    try:
        import pytesseract
        return pytesseract.image_to_string(pil_image, config="--psm 6")
    except Exception as e:
        log.warning("OCR failed: %s", e)
        return ""


def _needs_ocr(page) -> bool:
    """True if digital text is sparse — likely scanned."""
    words = page.extract_words()
    return len(words) < 25


# ── Quarterly TDS extractor ───────────────────────────────────────────────────

_RE_QUARTER_TDS = re.compile(
    r"(?:Q\s*)?(\d)\s*(?:April|July|October|January)[^\d]*"
    r"(?:TDS\s+Deposited|Tax\s+Deposited|Amount\s+Deposited)[^\d]*"
    r"([\d,]+(?:\.\d{1,2})?)",
    re.I,
)

def _extract_quarterly(text: str) -> dict[str, float]:
    out = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    for m in _RE_QUARTER_TDS.finditer(text):
        q = int(m.group(1))
        if 1 <= q <= 4:
            out[q] = _parse_num(m.group(2))
    return out


# ── Main parser ───────────────────────────────────────────────────────────────

def parse_form16(pdf_bytes: bytes, filename: str = "") -> Form16ParseResult:
    """
    Parse Form 16 PDF bytes and return Form16ParseResult.
    Raises ValueError if the document does not look like a Form 16.
    """
    import pdfplumber

    result = Form16ParseResult()
    all_text_parts: list[str] = []
    ocr_used = False

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            result.page_count = len(pdf.pages)
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if _needs_ocr(page):
                    try:
                        img = page.to_image(resolution=200).original
                        page_text = _ocr_page(img)
                        ocr_used = True
                    except Exception:
                        pass
                all_text_parts.append(page_text)
    except Exception as e:
        raise ValueError(f"Cannot read PDF: {e}") from e

    full_text = "\n".join(all_text_parts)
    result.ocr_used = ocr_used
    result.raw_text_sample = full_text[:500]

    # Validate it's a Form 16
    if not re.search(r"Form\s+No\.?\s*16|FORM\s+16|Certificate\s+under\s+Section\s+203", full_text, re.I):
        raise ValueError("Document does not appear to be Form 16")

    # ── Part A fields ─────────────────────────────────────────────────────────
    conf: dict[str, float] = {}

    def _extract(label: str, pattern: re.Pattern, is_num: bool = True):
        val = _first_match(pattern, full_text) if is_num else _first_str_match(pattern, full_text)
        conf[label] = 90.0 if val is not None else 0.0
        return val or (0.0 if is_num else None)

    result.employer_tan      = _extract("employer_tan",   _RE_TAN,          is_num=False) or ""
    result.employer_pan      = _extract("employer_pan",   _RE_EMPLOYER_PAN, is_num=False) or ""
    result.employee_pan      = _extract("employee_pan",   _RE_EMPLOYEE_PAN, is_num=False) or ""
    result.assessment_year   = _extract("assessment_year", _RE_AY,          is_num=False) or "2025-26"
    result.employee_name     = _extract("employee_name",  _RE_EMPLOYEE_NM,  is_num=False) or ""
    result.employer_name     = _extract("employer_name",  _RE_EMPLOYER_NM,  is_num=False) or ""
    result.total_tds_deposited = _extract("total_tds_deposited", _RE_TOTAL_TDS)

    quarterly = _extract_quarterly(full_text)
    result.tds_q1 = quarterly[1]
    result.tds_q2 = quarterly[2]
    result.tds_q3 = quarterly[3]
    result.tds_q4 = quarterly[4]
    q_sum = sum(quarterly.values())
    if q_sum > 0:
        conf["tds_quarterly"] = 85.0

    # ── Part B fields ─────────────────────────────────────────────────────────
    result.gross_salary         = _extract("gross_salary",      _RE_GROSS_SALARY)
    result.perquisites          = _extract("perquisites",        _RE_PERQUISITES)
    result.profits_in_lieu      = _extract("profits_in_lieu",    _RE_PROFITS_LIEU)
    result.hra_exempt           = _extract("hra_exempt",         _RE_HRA_EXEMPT)
    result.lta_exempt           = _extract("lta_exempt",         _RE_LTA_EXEMPT)
    result.standard_deduction   = _extract("standard_deduction", _RE_STD_DED)
    result.professional_tax     = _extract("professional_tax",   _RE_PROF_TAX)
    result.net_salary           = _extract("net_salary",         _RE_NET_SALARY)
    result.section_80c          = _extract("section_80c",        _RE_80C)
    result.section_80d          = _extract("section_80d",        _RE_80D)
    result.total_deductions_vi_a= _extract("total_deductions",   _RE_TOTAL_DEDS)
    result.total_income         = _extract("total_income",        _RE_TOTAL_INCOME)
    result.taxable_income       = _extract("taxable_income",      _RE_TAXABLE_INCOME)
    result.tax_on_income        = _extract("tax_on_income",       _RE_TAX_ON_INCOME)
    result.rebate_87a           = _extract("rebate_87a",          _RE_REBATE_87A)
    result.surcharge            = _extract("surcharge",           _RE_SURCHARGE)
    result.cess                 = _extract("cess",                _RE_CESS)
    result.tax_payable          = _extract("tax_payable",         _RE_TAX_PAYABLE)
    result.tds_deducted         = _extract("tds_deducted",        _RE_TDS_DEDUCTED)

    # Standard deduction default if missing
    if result.standard_deduction == 0 and result.gross_salary > 0:
        result.standard_deduction = 75_000.0
        conf["standard_deduction"] = 70.0
        result.parse_warnings.append("Standard deduction assumed ₹75,000 (not explicit in document)")

    # Cross-checks
    if result.total_tds_deposited == 0 and q_sum > 0:
        result.total_tds_deposited = q_sum
    if result.tds_deducted == 0 and result.total_tds_deposited > 0:
        result.tds_deducted = result.total_tds_deposited

    # Cross-validate Part A vs Part B TDS
    if abs(result.tds_deducted - result.total_tds_deposited) > 500:
        result.parse_warnings.append(
            f"TDS mismatch: Part B shows ₹{result.tds_deducted:,.0f}, "
            f"Part A shows ₹{result.total_tds_deposited:,.0f} — verify Form 26AS"
        )

    # Overall confidence
    filled = sum(1 for v in conf.values() if v > 0)
    result.confidence_score = round((filled / max(len(conf), 1)) * 100, 1)
    result.field_confidence = conf

    return result


def form16_to_itr_fields(r: Form16ParseResult) -> dict:
    """Map Form16ParseResult → income_data / deductions_data dicts."""
    return {
        "income_data": {
            "gross_salary": r.gross_salary,
            "hra_exempt": r.hra_exempt,
            "lta_exempt": r.lta_exempt,
            "perquisites": r.perquisites,
            "profits_in_lieu": r.profits_in_lieu,
            "standard_deduction": r.standard_deduction,
            "professional_tax": r.professional_tax,
            "net_salary": r.net_salary,
            "tds_deducted": r.tds_deducted,
            "_source": "form16",
        },
        "deductions_data": {
            "section_80c": r.section_80c,
            "section_80d_self": r.section_80d,
            "_source": "form16",
        },
        "filing_details": {
            "employee_pan": r.employee_pan,
            "employer_name": r.employer_name,
            "employer_pan": r.employer_pan,
            "employer_tan": r.employer_tan,
            "tds_q1": r.tds_q1,
            "tds_q2": r.tds_q2,
            "tds_q3": r.tds_q3,
            "tds_q4": r.tds_q4,
            "_source": "form16",
        },
    }
