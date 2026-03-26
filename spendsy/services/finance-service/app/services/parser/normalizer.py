from dataclasses import dataclass, field, asdict
from typing import Optional, List
from datetime import datetime
import re
from dateutil import parser as dateparser
import logging

logger = logging.getLogger("finance.parser.normalizer")

@dataclass
class Transaction:
    date: str                    # Always ISO 8601: YYYY-MM-DD
    description: str             # Cleaned, trimmed
    type: str                    # credit | debit | fee | interest | transfer | unknown
    amount: float                # Always positive; direction encoded in type
    running_balance: Optional[float] = None
    reference: Optional[str] = None

@dataclass
class NormalizedDocument:
    pdf_type: str                # ocr_scanned | structured_ledger | unstructured_text
    document_type: str           # e.g. "bank_statement", "invoice", "ledger"
    source_institution: Optional[str]
    statement_period_from: Optional[str]   # ISO 8601
    statement_period_to: Optional[str]     # ISO 8601
    account_id: Optional[str]
    currency: str                # ISO 4217: USD, EUR, GBP...
    opening_balance: Optional[float]
    closing_balance: Optional[float]
    transactions: List[Transaction]
    extraction_confidence: str   # high | medium | low
    extraction_notes: Optional[str]
    processed_at: str            # ISO 8601 timestamp

TRANSACTION_TYPE_MAP = {
    "cr": "credit", "credit": "credit", "deposit": "credit",
    "in": "credit", "+": "credit", "received": "credit",
    "dr": "debit", "debit": "debit", "withdrawal": "debit",
    "out": "debit", "-": "debit", "paid": "debit",
    "fee": "fee", "charge": "fee", "commission": "fee",
    "interest": "interest", "int": "interest",
    "transfer": "transfer", "trf": "transfer",
}

CURRENCY_MAP = {
    "$": "USD", "£": "GBP", "€": "EUR", "₹": "INR",
    "us dollar": "USD", "euro": "EUR", "pound": "GBP", "rupee": "INR", "inr": "INR"
}

def normalize_date(raw: str) -> str | None:
    if not raw or str(raw).lower() in ("unknown", "null", "none", ""):
        return None
    try:
        # Using dateutil parser with dayfirst=False by default (common for US, but we can adjust if needed)
        return dateparser.parse(str(raw), fuzzy=True).strftime("%Y-%m-%d")
    except Exception as e:
        logger.warning(f"Failed to normalize date '{raw}': {e}")
        return None

def normalize_amount(raw) -> float | None:
    if raw in (None, "", "null", "None"):
        return None
    
    # Early exit if already numeric
    if isinstance(raw, (int, float)):
        return abs(float(raw))

    s = str(raw).strip()
    
    # Handle European format: 1.234,56 → 1234.56
    # Pattern: Digit(s), then (Dot then 3 digits) one or more times, then optional (Comma then 2 digits)
    if re.match(r"^\d{1,3}(\.\d{3})+(,\d{2})?$", s):
        s = s.replace(".", "").replace(",", ".")
    else:
        # Otherwise assume standard or Indian format (1,23,456.78)
        s = s.replace(",", "")
        
    # Strip parentheses (accounting negatives) and symbols
    s = re.sub(r"[()$£€₹\s]", "", s).strip()
    
    try:
        return abs(float(s))
    except ValueError:
        logger.warning(f"Failed to normalize amount '{raw}'")
        return None

def normalize_type(raw: str) -> str:
    if not raw:
        return "unknown"
    return TRANSACTION_TYPE_MAP.get(str(raw).strip().lower(), "unknown")

def normalize_currency(raw: str) -> str:
    if not raw:
        return "USD"
    cleaned = str(raw).strip().lower()
    if cleaned in CURRENCY_MAP:
        return CURRENCY_MAP[cleaned]
    # Check if it's already an ISO code
    if len(cleaned) == 3:
        return cleaned.upper()
    return "USD"

def normalize_document(raw_json: dict, pdf_type: str) -> NormalizedDocument:
    """
    Normalizes raw LLM JSON output into a canonical NormalizedDocument dataclass.
    """
    txns = []
    for t in raw_json.get("transactions", []):
        txns.append(Transaction(
            date=normalize_date(t.get("date", "")) or "unknown",
            description=str(t.get("description") or "").strip(),
            type=normalize_type(t.get("type", "")),
            amount=normalize_amount(t.get("amount")) or 0.0,
            running_balance=normalize_amount(t.get("running_balance")),
            reference=str(t.get("reference") or "") if t.get("reference") else None,
        ))

    period = raw_json.get("statement_period") or {}
    
    return NormalizedDocument(
        pdf_type=pdf_type,
        document_type=str(raw_json.get("document_type", "unknown")),
        source_institution=raw_json.get("source_institution"),
        statement_period_from=normalize_date(period.get("from", "")),
        statement_period_to=normalize_date(period.get("to", "")),
        account_id=str(raw_json.get("account_id")) if raw_json.get("account_id") else None,
        currency=normalize_currency(raw_json.get("currency", "USD")),
        opening_balance=normalize_amount(raw_json.get("opening_balance")),
        closing_balance=normalize_amount(raw_json.get("closing_balance")),
        transactions=txns,
        extraction_confidence=str(raw_json.get("extraction_confidence", "low")),
        extraction_notes=raw_json.get("extraction_notes"),
        processed_at=datetime.utcnow().isoformat(),
    )
