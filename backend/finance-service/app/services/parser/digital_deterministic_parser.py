"""
digital_deterministic_parser.py
================================
Multi-bank coordinate-aware PDF bank statement parser for Indian banks.

Supports: HDFC, ICICI, SBI, Axis, Kotak, PNB, BoB, Canara, Union, BoI,
          Indian Bank, Yes Bank, IndusInd, IDFC FIRST, HSBC, Std Chartered,
          Citibank/Axis, SBI Card, ICICI CC, HDFC CC, Amex India.

Strategy (per reference spec):
  1. Detect PDF type (native / OCR) — raise OcrRequiredError if scanned
  2. Detect bank from signatures in first-page text
  3. Decrypt if password-protected (pikepdf, bank-specific password patterns)
  4. Find header row dynamically by scanning for bank-specific column keywords
  5. Extract column x-boundaries from header row words (±5 pt tolerance)
  6. Group body words into visual rows (y_tolerance=3 pt)
  7. Identify transaction rows by date pattern in Date column zone
  8. Merge multi-line narrations (rows between two date-rows)
  9. Parse amounts: strip commas, handle CR/DR suffixes
 10. Validate: opening_balance + credits - debits ≈ closing_balance

All pdfplumber coordinates are top-left origin (top increases downward).
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pdfplumber

from app.utils.ocr_detector import OcrRequiredError, classify_pdf_from_pdf

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Bank signatures & column schemas
# ─────────────────────────────────────────────────────────────────────────────

BANK_SIGNATURES: dict[str, list[str]] = {
    "HDFC":      ["HDFC BANK", "Withdrawal Amt", "Deposit Amt", "HDFC0"],
    "ICICI":     ["ICICI BANK", "ICICI0", "iMobile"],
    "SBI":       ["STATE BANK OF INDIA", "SBIN0", "Txn Date", "Value Date"],
    "AXIS":      ["AXIS BANK", "UTIB0", "Tran Date", "Withdrawals (Dr)"],
    "KOTAK":     ["KOTAK MAHINDRA", "KKBK0", "Dr Amt", "Cr Amt"],
    "PNB":       ["PUNJAB NATIONAL", "PUNB0", "Particulars", "Debit Amount"],
    "BOB":       ["BANK OF BARODA", "BARB0"],
    "CANARA":    ["CANARA BANK", "CNRB0"],
    "UNION":     ["UNION BANK", "UBIN0"],
    "BOI":       ["BANK OF INDIA", "BKID0"],
    "INDIAN":    ["INDIAN BANK", "IDIB0"],
    "YES":       ["YES BANK", "YESB0"],
    "INDUSIND":  ["INDUSIND BANK", "INDB0"],
    "IDFCFIRST": ["IDFC FIRST", "IDFB0"],
    "HSBC":      ["HSBC", "HSBC0"],
    "SCB":       ["STANDARD CHARTERED", "SCBL0"],
    "CITI":      ["CITIBANK", "CITI0"],
    "SBI_CARD":  ["SBI CARD", "SBI Cards", "Minimum Amount Due"],
    "ICICI_CC":  ["ICICI CREDIT", "One Card", "Amazon Pay ICICI"],
    "HDFC_CC":   ["HDFC CREDIT", "Reward Pt", "Transaction Description"],
    "AMEX":      ["AMERICAN EXPRESS", "AMEX"],
}

# Per-bank column header keywords used for dynamic header detection.
# Order matters: first match wins in _find_header_row().
BANK_HEADER_KEYWORDS: dict[str, list[str]] = {
    "HDFC":      ["Date", "Narration", "Withdrawal", "Deposit", "Closing"],
    "ICICI":     ["Date", "Description", "Debit", "Credit", "Balance"],
    "SBI":       ["Txn", "Value", "Description", "Debit", "Credit", "Balance"],
    "AXIS":      ["Tran", "Particulars", "Withdrawals", "Deposits", "Balance"],
    "KOTAK":     ["Dt", "Description", "Dr", "Cr", "Balance"],
    "PNB":       ["Date", "Amount", "Type", "Balance", "Remarks"],
    "BOB":       ["Date", "Narration", "Debit", "Credit", "Balance"],
    "CANARA":    ["Date", "Narration", "Debit", "Credit", "Balance"],
    "UNION":     ["Date", "Narration", "Dr", "Cr", "Balance"],
    "BOI":       ["Date", "Particulars", "Debit", "Credit", "Balance"],
    "INDIAN":    ["Date", "Narration", "Debit", "Credit", "Balance"],
    "YES":       ["Date", "Description", "Debit", "Credit", "Balance"],
    "INDUSIND":  ["Date", "Narration", "Debit", "Credit", "Balance"],
    "IDFCFIRST": ["Date", "Details", "Amount", "Type", "Balance"],
    "HSBC":      ["Date", "Description", "Amount", "Balance"],
    "SCB":       ["Transaction", "Description", "Debit", "Credit", "Balance"],
    "CITI":      ["Date", "Description", "Debit", "Credit", "Balance"],
    "SBI_CARD":  ["Date", "Transaction", "Amount"],
    "ICICI_CC":  ["Date", "Description", "Amount"],
    "HDFC_CC":   ["Date", "Transaction", "Reward", "Amount"],
    "AMEX":      ["Date", "Description", "Amount"],
    "UNKNOWN":   ["Date", "Description", "Debit", "Credit", "Balance"],
}

# Fallback static column zones (x0, x1) keyed by logical column name.
# Used when dynamic header detection fails.
BANK_COLUMN_ZONES: dict[str, dict[str, tuple[float, float]]] = {
    "HDFC": {
        "date":        (28,  85),
        "narration":   (85,  295),
        "ref":         (295, 370),
        "value_date":  (370, 420),
        "debit":       (420, 480),
        "credit":      (480, 535),
        "balance":     (535, 567),
    },
    "ICICI": {
        "date":        (36,  90),
        "description": (90,  290),
        "ref":         (290, 365),
        "value_date":  (365, 415),
        "debit":       (415, 475),
        "credit":      (475, 530),
        "balance":     (530, 559),
    },
    "SBI": {
        "txn_date":    (28,  88),   # anchor: x0 < 88 only — ignore Value Date at 88-148
        "value_date":  (88,  148),
        "description": (148, 330),
        "ref":         (330, 390),
        "debit":       (390, 455),
        "credit":      (455, 510),
        "balance":     (510, 567),
    },
    "AXIS": {
        "date":        (30,  90),
        "ref":         (90,  145),
        "narration":   (145, 330),
        "debit":       (330, 420),
        "credit":      (420, 495),
        "balance":     (495, 565),
    },
    "KOTAK": {
        "date":        (35,  88),
        "description": (88,  305),
        "ref":         (305, 355),
        "debit":       (355, 430),
        "credit":      (430, 500),
        "balance":     (500, 560),
    },
    "PNB": {
        # PNB ONE e-statement: single amount + DR/CR flag layout
        "date":        (40,  92),
        "amount":      (160, 232),
        "type":        (228, 268),   # "DR" or "CR" flag word
        "balance":     (265, 342),
        "narration":   (342, 567),
    },
    "BOB": {
        "date":        (30,  90),
        "narration":   (90,  295),
        "ref":         (295, 360),
        "debit":       (360, 430),
        "credit":      (430, 495),
        "balance":     (495, 565),
    },
    "CANARA": {
        "date":        (28,  88),
        "narration":   (88,  295),
        "ref":         (295, 360),
        "debit":       (360, 430),
        "credit":      (430, 495),
        "balance":     (495, 567),
    },
    "UNION": {
        "date":        (28,  88),
        "narration":   (88,  295),
        "ref":         (295, 360),
        "debit":       (360, 430),
        "credit":      (430, 495),
        "balance":     (495, 567),
    },
    "BOI": {
        "date":        (28,  88),
        "narration":   (88,  295),
        "ref":         (295, 360),
        "debit":       (360, 430),
        "credit":      (430, 495),
        "balance":     (495, 565),
    },
    "INDIAN": {
        "date":        (28,  88),
        "narration":   (88,  295),
        "ref":         (295, 360),
        "debit":       (360, 430),
        "credit":      (430, 495),
        "balance":     (495, 565),
    },
    "YES": {
        "date":        (28,  90),
        "description": (90,  290),
        "ref":         (290, 360),
        "debit":       (360, 430),
        "credit":      (430, 495),
        "balance":     (495, 567),
    },
    "INDUSIND": {
        "date":        (30,  90),
        "narration":   (90,  290),
        "ref":         (290, 360),
        "debit":       (360, 430),
        "credit":      (430, 495),
        "balance":     (495, 565),
    },
    "IDFCFIRST": {
        "date":        (30,  90),
        "details":     (90,  295),
        "amount":      (295, 430),
        "type":        (430, 465),
        "balance":     (465, 540),
    },
    "HSBC": {
        "date":        (42,  120),
        "description": (120, 430),
        "amount":      (430, 510),
        "balance":     (510, 567),
    },
    "SCB": {
        "date":        (36,  110),
        "description": (110, 360),
        "debit":       (360, 430),
        "credit":      (430, 495),
        "balance":     (495, 567),
    },
    "CITI": {
        "date":        (28,  90),
        "description": (90,  290),
        "debit":       (290, 390),
        "credit":      (390, 470),
        "balance":     (470, 567),
    },
    # Credit cards — single amount column
    "HDFC_CC": {
        "date":        (28,  85),
        "description": (85,  330),
        "reward":      (330, 400),
        "amount":      (400, 480),
        "flag":        (480, 567),
    },
    "SBI_CARD": {
        "date":        (28,  88),
        "description": (88,  460),
        "amount":      (460, 567),
    },
    "ICICI_CC": {
        "date":        (36,  90),
        "description": (90,  480),
        "amount":      (480, 567),
    },
    "AMEX": {
        "date":        (28,  90),
        "description": (90,  430),
        "amount":      (430, 567),
    },
}

# For banks not in the map, use a wide generic zone
_GENERIC_ZONES: dict[str, tuple[float, float]] = {
    "date":        (28,  90),
    "description": (90,  360),
    "debit":       (360, 460),
    "credit":      (460, 510),
    "balance":     (510, 567),
}

# Banks with SINGLE amount column (credit cards + HSBC + IDFC FIRST)
SINGLE_AMOUNT_BANKS = {"HDFC_CC", "SBI_CARD", "ICICI_CC", "AMEX", "HSBC", "IDFCFIRST", "PNB"}

# Banks where the FIRST date column is the transaction date, second is value date (ignore)
DUAL_DATE_BANKS = {"SBI", "BOI", "INDIAN"}


# ─────────────────────────────────────────────────────────────────────────────
# Date patterns
# ─────────────────────────────────────────────────────────────────────────────

DATE_PATTERNS = [
    (re.compile(r"\b(\d{2})/(\d{2})/(\d{2})\b"),     "%d/%m/%y"),   # HDFC savings old
    (re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b"),     "%d/%m/%Y"),   # most banks
    (re.compile(r"\b(\d{2})-(\d{2})-(\d{4})\b"),     "%d-%m-%Y"),   # Axis, Kotak
    (re.compile(r"\b(\d{2})-([A-Za-z]{3})-(\d{4})\b"), "%d-%b-%Y"), # Kotak month name
    (re.compile(r"\b(\d{2}) ([A-Za-z]{3}) (\d{4})\b"), "%d %b %Y"), # HSBC, Std Chart
    (re.compile(r"\b(\d{2})[A-Za-z]{3}\d{2,4}\b"),   None),         # 03Apr23 handled below
]

# Day+month-only patterns (credit cards — no year)
DATE_NO_YEAR_RE = re.compile(
    r"^\[?\s*"
    r"(?:\d{2}\s*[A-Za-z]{3}|\d{2}\s*[/\-.]\s*\d{2})"
    r"\s*(?:\||\])?$"
)

# General date token detector (loose — for identifying date-column words)
DATE_TOKEN_RE = re.compile(
    r"^\[?\s*"
    r"(?:"
    r"\d{2}[A-Za-z0-9/.\- ]*\d{2,4}"
    r"|\d{2}\s*[A-Za-z]{3}"
    r"|\d{2}\s*[/\-.]\s*\d{2}"
    r")"
    r"\s*(?:\||\])?$"
)

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

# Amount token: must have decimal OR be ≥5 digits (rejects card fragments like "4386")
AMOUNT_TOKEN_RE = re.compile(r"^\d[\d,]*\.\d{1,2}$|^\d{5,}[\d,]*$")

# Noise row patterns
NOISE_RE = re.compile(
    r"^("
    r"date|transaction\s+details?|particulars|narration|description"
    r"|withdrawals?|deposits?|debit\s+amount|credit\s+amount|balance"
    r"|opening\s+balance|closing\s+balance|closing\s+available"
    r"|funds\s+on\s+earmark|total|earmark|ref|chq|value\s+date"
    r"|page\s+\d|statement\s+period|your\s+\w+bank"
    r"|savings\s+account|credit\s+card\s+details"
    r"|banking\s+reward|home|citibank|axis\s+bank"
    r"|hdfc|icici|kotak|sbi|pnb|canara|baroda|union|indian\s+bank"
    r")\b",
    re.IGNORECASE,
)

# Credit/debit classification keywords
CREDIT_KEYWORDS = re.compile(
    r"\b(inward|salary[\s_]credit|credit[\s_]from|credited|received|"
    r"refund|reversal|cashback|interest[\s_]credit|neft[\s_]cr|"
    r"imps[\s_]inward|rtgs[\s_]inward|dividend|deposit|by\s+transfer|"
    r"by\s+clg|by\s+neft|by\s+rtgs|by\s+upi)\b",
    re.IGNORECASE,
)

DEBIT_KEYWORDS = re.compile(
    r"\b(outward|ecs[\s_]paid|nach|purchase|atm[\s_]withdrawal|"
    r"debit|dr\b|payment[\s_]for|imps[\s_]outward|neft[\s_]dr|"
    r"intercity[\s_]ecs|rtgs[\s_]outward|to\s+transfer|to\s+neft|"
    r"to\s+upi|withdrawal|pos\s+debit)\b",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Data model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Transaction:
    date:          str
    description:   str
    amount:        float
    type:          str            # "credit" | "debit"
    balance:       Optional[float] = None
    raw_date:      str = ""
    date_inferred: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParseResult:
    transactions:    list[Transaction] = field(default_factory=list)
    opening_balance: Optional[float]   = None
    closing_balance: Optional[float]   = None
    total_credits:   float             = 0.0
    total_debits:    float             = 0.0
    page_count:      int               = 0
    bank:            str               = "UNKNOWN"
    errors:          list[str]         = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["transaction_count"] = len(self.transactions)
        return d


# ─────────────────────────────────────────────────────────────────────────────
# Bank detection
# ─────────────────────────────────────────────────────────────────────────────

def detect_bank(full_text: str) -> str:
    text_upper = full_text.upper()
    for bank, signatures in BANK_SIGNATURES.items():
        if any(sig.upper() in text_upper for sig in signatures):
            return bank
    return "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# Amount parsing
# ─────────────────────────────────────────────────────────────────────────────

def _strip_cr_dr(text: str) -> tuple[str, Optional[str]]:
    """Strip trailing CR/DR suffix. Returns (cleaned_text, 'CR'|'DR'|None)."""
    m = re.match(r"^([\d,\.]+)(CR|DR)$", text.strip(), re.IGNORECASE)
    if m:
        return m.group(1), m.group(2).upper()
    # Parenthesised negatives (Amex): (1234.56) → debit
    m = re.match(r"^\((\d[\d,\.]*)\)$", text.strip())
    if m:
        return m.group(1), "DR"
    return text.strip(), None


def parse_amount(text: str, is_balance: bool = False) -> Optional[float]:
    if not text:
        return None
    text = re.sub(r"[\]\|\s\-]+$", "", text)
    text, _ = _strip_cr_dr(text)
    # pdfplumber misread: comma-as-decimal e.g. "92,00"
    if re.search(r",\d{2}$", text) and "." not in text:
        text = text[:-3] + "." + text[-2:]
    cleaned = text.replace(",", "").strip()
    # multiple decimals e.g. "1.43950.15"
    if cleaned.count(".") > 1:
        parts = cleaned.rsplit(".", 1)
        cleaned = parts[0].replace(".", "") + "." + parts[1]
    try:
        value = float(cleaned)
    except ValueError:
        return None
    # Missing-decimal fix for pdfplumber balance extractions > 1M without decimal
    if is_balance and "." not in cleaned and value > 1_000_000:
        value /= 100
    return value


def is_valid_amount_token(text: str) -> bool:
    text = re.sub(r"[\]\|\s\-]+$", "", text)
    text, _ = _strip_cr_dr(text)
    if re.search(r",\d{2}$", text) and "." not in text:
        text = text[:-3] + "." + text[-2:]
    cleaned = text.replace(",", "")
    if cleaned.count(".") > 1:
        parts = cleaned.rsplit(".", 1)
        cleaned = parts[0].replace(".", "") + "." + parts[1]
    return bool(AMOUNT_TOKEN_RE.match(cleaned))


# ─────────────────────────────────────────────────────────────────────────────
# Date parsing
# ─────────────────────────────────────────────────────────────────────────────

def normalise_date(raw: str) -> str:
    """Convert any Indian bank date format to YYYY-MM-DD. Returns '' on failure."""
    if not raw:
        return ""
    date_str = re.sub(r"^[\[\s\|]+|[\]\s\|]+$", "", raw.strip())
    if not date_str:
        return ""
    # Strip trailing time component "HH:MM:SS" or "HH:MM" before splitting
    date_str = re.sub(r"\s+\d{1,2}:\d{2}(:\d{2})?$", "", date_str).strip()
    date_str = date_str.split()[0]

    # ISO passthrough
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        pass

    # Pad single-digit day (e.g. 3Apr23 → 03Apr23)
    if len(date_str) >= 6 and date_str[0].isdigit() and not date_str[1].isdigit():
        date_str = "0" + date_str

    for fmt in (
        "%d%b%y", "%d%b%Y",
        "%d-%b-%y", "%d-%b-%Y",
        "%d/%b/%y", "%d/%b/%Y",
        "%d %b %y", "%d %b %Y",
        "%d/%m/%y", "%d/%m/%Y",
        "%d-%m-%y", "%d-%m-%Y",
        "%d.%m.%y", "%d.%m.%Y",
    ):
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Corrupted pdfplumber extraction e.g. "030072023" / "03072023"
    digits = re.sub(r"\D", "", date_str)
    if len(digits) in (8, 9):
        year = digits[-4:]
        month = digits[-6:-4]
        day = digits[:2]
        try:
            return datetime.strptime(f"{day}{month}{year}", "%d%m%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
    if len(digits) == 6:
        try:
            return datetime.strptime(digits, "%d%m%y").strftime("%Y-%m-%d")
        except ValueError:
            pass

    return ""


def extract_day_month_no_year(raw: str) -> Optional[tuple[int, int]]:
    """Pull (day, month) from a no-year token like '15APR' or '15/04'."""
    if not raw:
        return None
    s = re.sub(r"^[\[\s\|]+|[\]\s\|]+$", "", raw.strip())
    m = re.match(r"^(\d{2})\s*([A-Za-z]{3})$", s)
    if m:
        day = int(m.group(1))
        month_str = MONTH_MAP.get(m.group(2).lower())
        if month_str and 1 <= day <= 31:
            return (day, int(month_str))
    m = re.match(r"^(\d{2})\s*[/\-.]\s*(\d{2})$", s)
    if m:
        day, mon = int(m.group(1)), int(m.group(2))
        if 1 <= day <= 31 and 1 <= mon <= 12:
            return (day, mon)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Dynamic header detection
# ─────────────────────────────────────────────────────────────────────────────

def _find_header_row(
    page,
    keywords: list[str],
) -> tuple[Optional[dict[str, dict]], Optional[float]]:
    """
    Scan page words for a row that contains ≥ (len(keywords)-1) of the
    header keywords. Returns (col_map, header_y) where col_map maps each
    keyword to {'x0', 'x1', 'top'}.

    Uses top-left pdfplumber coordinates throughout.
    """
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    if not words:
        return None, None

    # Group by 4-pt y buckets
    rows: dict[float, list] = defaultdict(list)
    for w in words:
        bucket = round(w["top"] / 4) * 4
        rows[bucket].append(w)

    kw_lower = [k.lower() for k in keywords]
    for top in sorted(rows):
        row = rows[top]
        texts_lower = [w["text"].lower() for w in row]
        matches = sum(1 for k in kw_lower if any(k in t for t in texts_lower))
        if matches >= max(len(keywords) - 1, 2):
            col_map: dict[str, dict] = {}
            for w in sorted(row, key=lambda x: x["x0"]):
                wt = w["text"].lower()
                for k in kw_lower:
                    if k in wt and k not in col_map:
                        col_map[k] = {"x0": w["x0"], "x1": w["x1"], "top": top}
                        break
            return col_map, float(top)

    return None, None


def _zones_from_col_map(
    col_map: dict[str, dict],
    page_width: float,
) -> dict[str, tuple[float, float]]:
    """
    Convert header word positions into (x0, x1) zones with ±5pt tolerance.
    Each column zone extends from its x0 to the next column's x0.

    The first column always starts at x=0 so data words that are slightly
    left of the header word (e.g. PNB dates at x=43 while header starts
    at x=56) are still captured correctly.
    """
    cols = sorted(col_map.items(), key=lambda kv: kv[1]["x0"])
    zones: dict[str, tuple[float, float]] = {}
    for i, (name, pos) in enumerate(cols):
        # First column: anchor to 0 so data never falls left of the zone.
        # Other columns: 15pt left padding to handle alignment variance.
        if i == 0:
            x0 = 0.0
        else:
            x0 = max(0.0, pos["x0"] - 15)
        x1 = (cols[i + 1][1]["x0"] - 15) if i + 1 < len(cols) else page_width
        zones[name] = (x0, x1)

    # "remarks" is a narration alias used by PNB — remap so desc_parts are
    # populated correctly by parse_page which checks for "narration" zone.
    if "remarks" in zones and "narration" not in zones:
        zones["narration"] = zones.pop("remarks")

    return zones


# ─────────────────────────────────────────────────────────────────────────────
# Row grouping & column assignment
# ─────────────────────────────────────────────────────────────────────────────

def group_words_by_row(words: list, tolerance: float = 3.0) -> dict[float, list]:
    rows: dict[float, list] = defaultdict(list)
    for w in words:
        key = round(w["top"] / tolerance) * tolerance
        rows[key].append(w)
    return dict(sorted(rows.items()))


def assign_to_zone(x0: float, zones: dict[str, tuple[float, float]]) -> Optional[str]:
    """Return zone name whose x-range contains x0, or None.

    Uses a 2pt right-side slop so words that land exactly on a zone
    boundary (due to pdfplumber sub-pixel rounding) still get assigned.
    """
    best_name: Optional[str] = None
    best_dist = float("inf")
    for name, (zx0, zx1) in zones.items():
        if zx0 <= x0 < zx1 + 2:          # 2pt slop on right edge
            dist = x0 - zx0               # prefer leftmost matching zone
            if dist < best_dist:
                best_dist = dist
                best_name = name
    return best_name


# ─────────────────────────────────────────────────────────────────────────────
# Credit/debit classification
# ─────────────────────────────────────────────────────────────────────────────

def classify_type(
    description: str,
    debit_val: Optional[float],
    credit_val: Optional[float],
    cr_dr_suffix: Optional[str],
    bank: str,
) -> str:
    """
    Determine credit vs debit.
    Priority: explicit DR/CR suffix > separate debit/credit column values > keywords.
    """
    if cr_dr_suffix == "CR":
        return "credit"
    if cr_dr_suffix == "DR":
        return "debit"
    if credit_val and credit_val > 0 and (not debit_val or debit_val == 0):
        return "credit"
    if debit_val and debit_val > 0 and (not credit_val or credit_val == 0):
        return "debit"
    if CREDIT_KEYWORDS.search(description):
        return "credit"
    return "debit"


# ─────────────────────────────────────────────────────────────────────────────
# Summary extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_summary(text: str) -> dict[str, Optional[float]]:
    """Extract opening / closing balance from raw page text.

    Handles multiple statement formats:
      • Explicit labels: "Opening Balance: 12,345.67"
      • Axis/HDFC variant: "Bal. Brought Forward 12345.67"
      • Kotak: "Opening Bal 12,345.67"
      • ICICI: "Opening Balance(INR) 12,345.67"
      • Available balance lines
    """
    result: dict[str, Optional[float]] = {}

    ob_patterns = [
        r"opening\s+balance\s*(?:\(INR\))?[:\s]+([0-9,]+\.[0-9]{2})",
        r"bal(?:ance)?[\s.]+brought\s+forward[:\s]+([0-9,]+\.[0-9]{2})",
        r"opening\s+bal[:\s]+([0-9,]+\.[0-9]{2})",
        r"b/f[:\s]+([0-9,]+\.[0-9]{2})",
        r"brought\s+forward[:\s]+([0-9,]+\.[0-9]{2})",
    ]
    cb_patterns = [
        r"closing\s+(?:available\s+)?balance\s*(?:\(INR\))?[:\s]+([0-9,]+\.[0-9]{2})",
        r"closing\s+bal[:\s]+([0-9,]+\.[0-9]{2})",
        r"balance\s+carried\s+forward[:\s]+([0-9,]+\.[0-9]{2})",
        r"c/f[:\s]+([0-9,]+\.[0-9]{2})",
        r"available\s+balance[:\s]+([0-9,]+\.[0-9]{2})",
    ]
    for pat in ob_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["opening_balance"] = parse_amount(m.group(1))
            break
    for pat in cb_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["closing_balance"] = parse_amount(m.group(1))
            break
    return result


# ─────────────────────────────────────────────────────────────────────────────
# OCR check
# ─────────────────────────────────────────────────────────────────────────────

def check_digital(pdf: Any) -> bool:
    is_ocr, debug_info = classify_pdf_from_pdf(pdf)
    log.info("OCR detection: %s", json.dumps(debug_info, sort_keys=True))
    if is_ocr:
        raise OcrRequiredError(debug_info)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Page parser
# ─────────────────────────────────────────────────────────────────────────────

def _is_noise(text: str) -> bool:
    return bool(NOISE_RE.match(text.strip()))


def parse_page(
    page,
    bank: str,
    zones: dict[str, tuple[float, float]],
    header_y: Optional[float],
    is_cc: bool,
) -> tuple[list[dict], str]:
    """
    Parse one page into logical transaction rows.

    Returns (logical_rows, raw_page_text).

    Each logical_row dict:
      raw_date, date, desc_parts, debit, credit, balance, amount (CC),
      cr_dr_suffix, raw_amounts
    """
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    raw_text = page.extract_text() or ""
    if not words:
        return [], raw_text

    # Only look at words below the header row
    if header_y is not None:
        words = [w for w in words if w["top"] > header_y + 2]

    visual_rows = group_words_by_row(words, tolerance=3.0)

    # SBI / BOI / INDIAN have two date columns — skip the second (value date)
    dual_date = bank in DUAL_DATE_BANKS
    date_zone = zones.get("txn_date") or zones.get("date") or (0, 90)

    logical_rows: list[dict] = []
    current: Optional[dict] = None

    for _top, row_words in visual_rows.items():
        row_words_sorted = sorted(row_words, key=lambda w: w["x0"])

        date_parts:   list[str] = []
        desc_parts:   list[str] = []
        debit_parts:  list[str] = []
        credit_parts: list[str] = []
        balance_parts: list[str] = []
        amount_parts: list[str] = []   # single-amount-column banks
        cr_dr_suffix: Optional[str] = None  # set by "type" zone or post-loop

        for w in row_words_sorted:
            x, text = w["x0"], w["text"]
            zone = assign_to_zone(x, zones)

            if zone in ("date", "txn_date"):
                # Dual-date banks: only accept words in the FIRST date zone
                if dual_date and x > date_zone[1]:
                    continue
                if DATE_TOKEN_RE.match(text):
                    date_parts.append(text)
                else:
                    desc_parts.append(text)

            elif zone in ("narration", "description", "particulars", "details"):
                desc_parts.append(text)

            elif zone in ("debit", "withdrawal", "withdrawals", "dr", "dr_amt"):
                if is_valid_amount_token(text):
                    debit_parts.append(text)

            elif zone in ("credit", "deposit", "deposits", "cr", "cr_amt"):
                if is_valid_amount_token(text):
                    credit_parts.append(text)

            elif zone == "balance":
                if is_valid_amount_token(text):
                    balance_parts.append(text)
                # Indian Bank: balance has fused CR e.g. "1234.56CR" — handled in parse_amount
                elif re.match(r"^\d[\d,\.]+CR$", text, re.IGNORECASE):
                    balance_parts.append(text)

            elif zone == "amount":
                # Single-amount column (CC + HSBC + IDFC FIRST)
                if is_valid_amount_token(text) or re.match(r"^\d[\d,\.]+CR$", text, re.IGNORECASE) or re.match(r"^\(\d", text):
                    amount_parts.append(text)

            elif zone == "type":
                # Explicit DR/CR flag column (PNB ONE, IDFC FIRST)
                t = text.strip().upper()
                if t in ("DR", "CR"):
                    cr_dr_suffix = t

            elif zone in ("ref", "value_date", "reward", "flag"):
                pass  # skip ref/value-date/reward-points columns

            else:
                # Unzoned word — be conservative.
                # Only treat as an amount candidate if:
                #   1. We have no amount yet (prevents balance from clobbering)
                #   2. It's clearly numeric
                #   3. It's well into the right half of the page (x > 300)
                # Otherwise it goes into desc_parts (worse to lose an amount
                # than to corrupt one, since desc_parts are just for display).
                if (x > 300 and is_valid_amount_token(text)
                        and not amount_parts and not debit_parts and not credit_parts):
                    amount_parts.append(text)
                elif x >= (date_zone[1] if date_zone else 90):
                    desc_parts.append(text)

        date_str  = " ".join(date_parts).strip()
        desc      = " ".join(desc_parts).strip()
        debit_raw  = debit_parts[0]  if debit_parts  else ""
        credit_raw = credit_parts[0] if credit_parts else ""
        balance_raw = balance_parts[-1] if balance_parts else ""  # take rightmost

        # CR/DR suffix — may already be set by "type" zone (PNB, IDFC FIRST).
        # Also try to extract from fused amount token e.g. "1234.56CR".
        amount_raw = ""
        if amount_parts:
            raw_amt, suffix_from_amount = _strip_cr_dr(amount_parts[-1])
            amount_raw = raw_amt
            if cr_dr_suffix is None:
                cr_dr_suffix = suffix_from_amount

        # ── New transaction row ──────────────────────────────────────────────
        if DATE_TOKEN_RE.match(date_str):
            if current:
                logical_rows.append(current)
            current = {
                "raw_date":     date_str,
                "date":         normalise_date(date_str),
                "desc_parts":   [desc] if desc else [],
                "debit":        parse_amount(debit_raw),
                "credit":       parse_amount(credit_raw),
                "balance":      parse_amount(balance_raw, is_balance=True),
                "amount":       parse_amount(amount_raw),
                "cr_dr_suffix": cr_dr_suffix,
            }

        # ── Continuation row ─────────────────────────────────────────────────
        elif current is not None:
            if _is_noise(desc) and not any([debit_raw, credit_raw, balance_raw, amount_raw]):
                continue
            if desc and not _is_noise(desc):
                current["desc_parts"].append(desc)

            # Propagate amounts from continuation if parent missing them
            if debit_raw and current["debit"] is None:
                current["debit"] = parse_amount(debit_raw)
            if credit_raw and current["credit"] is None:
                current["credit"] = parse_amount(credit_raw)
            if balance_raw and current["balance"] is None:
                current["balance"] = parse_amount(balance_raw, is_balance=True)
            if amount_raw and current["amount"] is None:
                current["amount"] = parse_amount(amount_raw)
            if cr_dr_suffix and current["cr_dr_suffix"] is None:
                current["cr_dr_suffix"] = cr_dr_suffix

    if current:
        logical_rows.append(current)

    return logical_rows, raw_text


# ─────────────────────────────────────────────────────────────────────────────
# Date inference pass
# ─────────────────────────────────────────────────────────────────────────────

def _infer_dates(all_rows: list[dict]) -> None:
    """
    Fill missing dates in-place:
    - day+month-only tokens: inherit year from last good row, handle year rollover
    - completely unparseable: inherit month/year, day=01, flag date_inferred=True
    """
    last_good_ymd: Optional[tuple[int, int, int]] = None

    for row in all_rows:
        if row.get("date"):
            try:
                dt = datetime.strptime(row["date"], "%Y-%m-%d")
                last_good_ymd = (dt.year, dt.month, dt.day)
                row["date_inferred"] = False
            except ValueError:
                pass
            continue

        dm = extract_day_month_no_year(row.get("raw_date", ""))
        if dm is not None and last_good_ymd is not None:
            day, month = dm
            year = last_good_ymd[0]
            # Year rollover: handle statements that cross a Dec→Jan boundary.
            # Most Indian bank statements are oldest-first (forward chronological).
            # If the current month is January (1) and last seen was December (12) →
            # year has ticked forward. The reverse (Dec after Jan) means backward stmt.
            last_month = last_good_ymd[1]
            if last_month == 12 and month == 1:
                year += 1  # crossed Dec→Jan going forward
            elif last_month == 1 and month == 12:
                year -= 1  # crossed Jan→Dec going backward (reverse-chron stmt)
            # Clamp day to valid range (avoid day=00 from corrupted extractions)
            day = max(1, day)
            try:
                datetime(year, month, day)
                row["date"] = f"{year:04d}-{month:02d}-{day:02d}"
                row["date_inferred"] = False
                last_good_ymd = (year, month, day)
                continue
            except ValueError:
                pass

        if last_good_ymd is not None:
            y, m, _ = last_good_ymd
            row["date"] = f"{y:04d}-{m:02d}-01"
            row["date_inferred"] = True
        else:
            row["date_inferred"] = False


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_balance(result: "ParseResult") -> Optional[str]:
    """
    Golden rule: opening_balance + total_credits - total_debits ≈ closing_balance.
    Returns None if OK, or a warning string if mismatch > ₹1.
    """
    if result.opening_balance is None or result.closing_balance is None:
        return None
    computed = result.opening_balance + result.total_credits - result.total_debits
    diff = abs(computed - result.closing_balance)
    if diff > 1.0:
        return (
            f"Balance mismatch ₹{diff:,.2f}: "
            f"opening({result.opening_balance:,.2f}) + credits({result.total_credits:,.2f}) "
            f"- debits({result.total_debits:,.2f}) = {computed:,.2f} "
            f"≠ closing({result.closing_balance:,.2f})"
        )
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def parse_statement(pdf_path: str) -> ParseResult:
    """
    Parse a digital Indian bank statement PDF.

    Raises:
      FileNotFoundError  — path doesn't exist
      OcrRequiredError   — scanned/image PDF detected
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    result = ParseResult()
    all_raw_text: list[str] = []
    all_logical_rows: list[dict] = []

    with pdfplumber.open(str(path)) as pdf:
        result.page_count = len(pdf.pages)
        check_digital(pdf)

        # Bank detection from first-page text
        first_text = pdf.pages[0].extract_text() or "" if pdf.pages else ""
        bank = detect_bank(first_text)
        result.bank = bank
        log.info("Detected bank: %s", bank)

        is_cc = bank in SINGLE_AMOUNT_BANKS
        header_keywords = BANK_HEADER_KEYWORDS.get(bank, BANK_HEADER_KEYWORDS["UNKNOWN"])
        static_zones = BANK_COLUMN_ZONES.get(bank, _GENERIC_ZONES)

        # Per-page parse
        for page_num, page in enumerate(pdf.pages):
            try:
                # Dynamic header detection — prefer dynamic over static.
                # Guard: only trust the detected header if it sits in the TOP
                # 50% of the page.  On some statements (e.g. PNB ONE) the
                # first page has a long preamble that pushes the table header
                # below the midpoint; the dynamic zones built from that
                # position are misaligned because the data text wraps across
                # what the detector thinks is the narration column.  Falling
                # back to static zones gives correct column boundaries.
                col_map, header_y = _find_header_row(page, header_keywords)
                page_height = float(page.height)
                header_in_top_half = (header_y is not None and header_y < page_height * 0.50)
                if col_map and header_in_top_half:
                    zones = _zones_from_col_map(col_map, float(page.width))
                    log.debug("Page %d: dynamic zones %s (header_y=%.1f)", page_num + 1, zones, header_y)
                else:
                    zones = static_zones
                    # IMPORTANT: still pass the detected header_y to parse_page
                    # even when falling back to static zones. This ensures words
                    # above the table (branch name, customer address on page 1)
                    # are skipped by the header_y cutoff in parse_page.
                    # header_y is already set from _find_header_row above.
                    log.debug("Page %d: static zones for %s (header_y=%s)", page_num + 1, bank, header_y)

                logical_rows, raw_text = parse_page(page, bank, zones, header_y, is_cc)
                all_logical_rows.extend(logical_rows)
                all_raw_text.append(raw_text)

            except Exception as e:
                result.errors.append(f"Page {page_num + 1}: {e}")
                log.warning("Page %d failed: %s", page_num + 1, e)

    # Summary balances
    full_text = "\n".join(all_raw_text)
    summary = extract_summary(full_text)
    result.opening_balance = summary.get("opening_balance")
    result.closing_balance = summary.get("closing_balance")

    # Date inference for rows with missing/partial dates
    _infer_dates(all_logical_rows)

    # Build Transaction objects
    for row in all_logical_rows:
        desc = " ".join(p for p in row["desc_parts"] if p).strip()
        desc = re.sub(r"\s{2,}", " ", desc)

        debit_val   = row.get("debit")
        credit_val  = row.get("credit")
        amount_val  = row.get("amount")  # single-amount-column banks
        balance_val = row.get("balance")
        suffix      = row.get("cr_dr_suffix")

        # Determine amount + type
        if is_cc or bank in SINGLE_AMOUNT_BANKS:
            amount = amount_val
            tx_type = classify_type(desc, None, None, suffix, bank)
        else:
            # Dual-column debit/credit
            if credit_val and (not debit_val or debit_val == 0):
                amount  = credit_val
                tx_type = "credit"
            elif debit_val and (not credit_val or credit_val == 0):
                amount  = debit_val
                tx_type = "debit"
            else:
                # Both present or both absent — fall back to keyword classification
                amount  = debit_val or credit_val or amount_val
                tx_type = classify_type(desc, debit_val, credit_val, suffix, bank)

        if amount is None or amount <= 0:
            log.debug("Skipping row with no amount: %s", desc[:60])
            continue
        if _is_noise(desc) and amount < 10:
            continue

        tx = Transaction(
            date          = row.get("date", ""),
            description   = desc,
            amount        = amount,
            type          = tx_type,
            balance       = balance_val,
            raw_date      = row.get("raw_date", ""),
            date_inferred = bool(row.get("date_inferred")),
        )
        result.transactions.append(tx)

        if tx_type == "credit":
            result.total_credits += amount
        else:
            result.total_debits += amount

    # Balance validation
    warn = validate_balance(result)
    if warn:
        result.errors.append(f"WARN: {warn}")
        log.warning(warn)

    log.info(
        "Parsed %d transactions (%d pages, bank=%s) | credits=%.2f debits=%.2f",
        len(result.transactions), result.page_count, result.bank,
        result.total_credits, result.total_debits,
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Compatibility wrapper
# ─────────────────────────────────────────────────────────────────────────────

def parse_transactions(file_content: bytes) -> dict:
    """Compatibility wrapper for routes_finance.py. Accepts bytes → returns dict."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_content)
        tmp.flush()
        tmp_path = tmp.name
    try:
        result = parse_statement(tmp_path)
        res_dict = result.to_dict()
        return {"transactions": res_dict.get("transactions", []), "meta": res_dict}
    finally:
        p = Path(tmp_path)
        if p.exists():
            p.unlink()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python digital_deterministic_parser.py <path_to_pdf> [--json]")
        sys.exit(1)

    pdf_path  = sys.argv[1]
    json_mode = "--json" in sys.argv

    try:
        result = parse_statement(pdf_path)
    except (FileNotFoundError, OcrRequiredError) as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if json_mode:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    else:
        print(f"\n{'─'*70}")
        print(f"  Bank Statement — {pdf_path}")
        print(f"{'─'*70}")
        print(f"  Pages parsed    : {result.page_count}")
        print(f"  Transactions    : {len(result.transactions)}")
        print(f"  Opening balance : {result.opening_balance:,.2f}" if result.opening_balance else "  Opening balance : —")
        print(f"  Closing balance : {result.closing_balance:,.2f}" if result.closing_balance else "  Closing balance : —")
        print(f"  Total credits   : {result.total_credits:,.2f}")
        print(f"  Total debits    : {result.total_debits:,.2f}")
        if result.errors:
            print(f"\n  Errors ({len(result.errors)}):")
            for e in result.errors:
                print(f"    • {e}")
        print(f"\n{'─'*70}")
        print(f"  {'DATE':<12} {'TYPE':<7} {'AMOUNT':>12}  {'BALANCE':>12}  DESCRIPTION")
        print(f"{'─'*70}")
        for tx in result.transactions:
            bal = f"{tx.balance:>12,.2f}" if tx.balance else f"{'—':>12}"
            print(
                f"  {tx.date:<12} {tx.type:<7} {tx.amount:>12,.2f}  {bal}  "
                f"{tx.description[:45]}"
            )
        print(f"{'─'*70}\n")
