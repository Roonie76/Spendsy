"""
High-performance structured bank statement parser using regex.

Handles text output where each row looks like:
    28/11/2025  270.00  DR  237.55  UPI/MERCHANT NAME HERE

Pipeline stage: runs exclusively on STRUCTURED / SEMI_STRUCTURED text.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Compiled patterns — built once at import time for maximum speed
# ---------------------------------------------------------------------------

# Date: DD/MM/YYYY  DD-MM-YYYY  DD/MM/YY  DD-MM-YY  YYYY-MM-DD
_DATE_PAT = re.compile(
    r"\b(?:"
    r"(\d{2})[/\-](\d{2})[/\-](\d{4})"   # DD/MM/YYYY
    r"|"
    r"(\d{2})[/\-](\d{2})[/\-](\d{2})"   # DD/MM/YY
    r"|"
    r"(\d{4})[/\-](\d{2})[/\-](\d{2})"   # YYYY-MM-DD
    r")\b"
)

# Signed monetary value — optional leading sign, optional ₹/INR/Rs., commas ok
_AMOUNT_PAT = re.compile(
    r"(?P<sign>[+-])?\s*"
    r"(?:₹|INR|Rs\.?)?\s*"
    r"(?P<digits>(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d{1,2})?)"
    r"(?:\s*(?P<brackets>\)))?"  # closing paren for (123.00) style negatives
)

# Transaction type marker (captured as its own token)
_TYPE_PAT = re.compile(r"\b(DR|CR|Debit|Credit|DEBIT|CREDIT|D|C)\b", re.IGNORECASE)

# A "row" heuristic: must contain a date AND an amount
_ROW_PAT = re.compile(
    r"^(?P<date_raw>(?:\d{2}[/\-]\d{2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2}))"
    r"(?P<rest>.+)$",
    re.MULTILINE,
)

# Summary/noise lines to skip
_SKIP_PAT = re.compile(
    r"^\s*(?:opening|closing|total|b/f|brought forward|available|statement|account|page|date\s+desc|narration|particulars)"
    r"\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class StructuredTransaction:
    date: str          # YYYY-MM-DD
    description: str
    debit: float | None
    credit: float | None
    balance: float | None


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

_DATE_FORMATS = (
    ("%d/%m/%Y", 3),
    ("%d-%m-%Y", 3),
    ("%d/%m/%y", 3),
    ("%d-%m-%y", 3),
    ("%Y/%m/%d", 3),
    ("%Y-%m-%d", 3),
)


def _parse_date(raw: str) -> str | None:
    """Return ISO date string or None on failure."""
    raw = raw.strip()
    for fmt, _ in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# Amount helpers
# ---------------------------------------------------------------------------

def _clean_amount(raw: str) -> Decimal | None:
    """Parse a numeric string, stripping currency symbols and commas."""
    raw = raw.strip()
    if not raw:
        return None
    # Strip currency prefix
    raw = re.sub(r"[₹$€£]|INR|Rs\.?", "", raw, flags=re.IGNORECASE).strip()
    # Remove commas (thousands separators)
    raw = raw.replace(",", "")
    # Handle parenthetical negatives: (250.00) → -250.00
    if raw.startswith("(") and raw.endswith(")"):
        raw = "-" + raw[1:-1]
    try:
        d = Decimal(raw)
        return d if d >= 0 else -d  # store absolute value; type determines sign
    except InvalidOperation:
        return None


def _amounts_from_tokens(tokens: list[str]) -> list[Decimal]:
    """Extract all valid numeric amounts from a token list."""
    amounts: list[Decimal] = []
    for tok in tokens:
        amt = _clean_amount(tok)
        if amt is not None and amt > 0:
            amounts.append(amt)
    return amounts


# ---------------------------------------------------------------------------
# Core row parser
# ---------------------------------------------------------------------------

def _extract_type(s: str) -> tuple[str | None, str]:
    """Return (DR|CR|None, string_with_type_removed)."""
    m = _TYPE_PAT.search(s)
    if not m:
        return None, s
    raw_type = m.group(1).upper()
    cleaned = s[: m.start()] + s[m.end() :]
    return raw_type, cleaned


# Strict row pattern for "Date Amount Type Balance Description"
_STRICT_ROW_PAT = re.compile(
    r"^(?P<date>\d{2}[/\-]\d{2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2})\s+"
    r"(?P<amount>[\d,.]+(?:\.\d+)?)\s+"
    r"(?P<type>DR|CR|Debit|Credit|DEBIT|CREDIT|D|C)\s+"
    r"(?P<balance>[\d,.]+(?:\.\d+)?)\s+"
    r"(?P<desc>.+)$",
    re.IGNORECASE
)

def _parse_row(line: str) -> StructuredTransaction | None:
    """Parse a single text line into a StructuredTransaction or None."""
    line = line.strip()
    if not line or _SKIP_PAT.match(line):
        return None

    # 1. Try strict parsing for the specific structure requested
    m = _STRICT_ROW_PAT.match(line)
    if m:
        iso_date = _parse_date(m.group("date"))
        if not iso_date:
            return None
            
        raw_amount = _clean_amount(m.group("amount"))
        raw_balance = _clean_amount(m.group("balance"))
        tx_type = m.group("type").upper()
        desc = m.group("desc").strip()
        
        if raw_amount is None:
            return None

        debit = float(raw_amount) if tx_type in ("DR", "DEBIT", "D") else None
        credit = float(raw_amount) if tx_type in ("CR", "CREDIT", "C") else None
        
        return StructuredTransaction(
            date=iso_date,
            description=desc[:255],
            debit=debit,
            credit=credit,
            balance=float(raw_balance) if raw_balance is not None else None
        )

    # 2. Fallback to heuristic parsing for variants
    m = _ROW_PAT.match(line)
    if not m:
        return None

    date_raw = m.group("date_raw")
    rest = m.group("rest").strip()

    iso_date = _parse_date(date_raw)
    if not iso_date:
        return None

    # Simplified heuristic: look for [Amount] [Type] [Balance]
    # We still want to be fast and safe.
    parts = rest.split()
    if len(parts) < 2:
        return None

    # Minimal heuristic: find the first amount and the first type marker
    # This is less reliable but handles slight variations
    try:
        txn_amount = None
        tx_type = None
        balance = None
        
        # Primitive token scanning
        remaining_tokens = []
        for i, token in enumerate(parts):
            if tx_type is None and _TYPE_PAT.fullmatch(token):
                tx_type = token.upper()
                continue
            
            amt = _clean_amount(token)
            if amt is not None:
                if txn_amount is None:
                    txn_amount = amt
                elif balance is None:
                    balance = amt
                continue
            
            remaining_tokens.append(token)
            
        if txn_amount is None or tx_type is None:
            return None

        desc = " ".join(remaining_tokens).strip() or "Transaction"
        
        debit = float(txn_amount) if tx_type in ("DR", "DEBIT", "D") else None
        credit = float(txn_amount) if tx_type in ("CR", "CREDIT", "C") else None

        return StructuredTransaction(
            date=iso_date,
            description=desc[:255],
            debit=debit,
            credit=credit,
            balance=float(balance) if balance is not None else None
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_structured_text(text: str) -> list[StructuredTransaction]:
    """
    Parse a block of structured bank statement text.

    Args:
        text: Raw multi-line text extracted from a PDF/CSV/plaintext file.

    Returns:
        List of StructuredTransaction dataclasses. Invalid lines are silently skipped.
    """
    if not text:
        return []

    results: list[StructuredTransaction] = []
    seen: set[tuple] = set()  # simple dedup key

    for line in text.splitlines():
        tx = _parse_row(line)
        if tx is None:
            continue

        key = (tx.date, tx.description[:60].lower(), tx.debit, tx.credit)
        if key in seen:
            logger.debug("Duplicate row skipped: %s", tx.date)
            continue
        seen.add(key)
        results.append(tx)

    logger.info("regex_parser: extracted %d transactions from %d lines", len(results), text.count("\n"))
    return results
