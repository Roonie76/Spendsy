"""
TYPE_A Parser — Structured table format for HDFC, ICICI, Axis, Kotak etc.

This parser handles bank statements where transactions are laid out in a
clean tabular structure with explicit column headers like:
    Date | Description/Narration | Debit/Withdrawal | Credit/Deposit | Balance

Strategy:
    1. Split text into lines
    2. Locate the header row by scanning for known column header keywords
    3. Parse each subsequent line using the discovered column positions
    4. Merge continuation lines (multi-line descriptions)
    5. Return a list of normalized StructuredTransaction objects

Fall back gracefully — any line that cannot be parsed is silently skipped
so partial extraction is always preferable to a complete failure.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Iterator, Any

from app.core.base_parser import BaseParser
from app.core.schemas import ParsedTransaction, ParserResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

# Date formats: DD/MM/YYYY, DD-MM-YYYY, DD/MM/YY, DD-MM-YY, YYYY-MM-DD,
# and textual variants like "28 Nov 2025" or "28-Nov-2025"
_DATE_PAT = re.compile(
    r"\b(?:"
    r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})"          # DD/MM/YYYY or DD-MM-YY
    r"|"
    r"(\d{4})[/\-](\d{2})[/\-](\d{2})"                 # YYYY-MM-DD
    r"|"
    r"(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})"  # DD Mon YYYY
    r")\b",
    re.IGNORECASE,
)

_AMOUNT_PAT = re.compile(
    r"(?:[₹$]|INR|Rs\.?)?\s*"
    r"(?P<sign>[+\-\(]?)\s*"
    r"(?P<digits>(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d{1,2})?)\s*(?P<close>\))?",
)

# Noise / summary lines to skip
_SKIP_PAT = re.compile(
    r"^\s*(?:opening|closing|total|b/f|brought\s+forward|available"
    r"|statement\s+date|account\s+(?:no|number)|page\s+\d|date\s+(?:desc|narr))",
    re.IGNORECASE,
)

# Column-header keywords (lowercase) mapped to semantic name
_HEADER_KEYWORDS = {
    "date": "date",
    "txn date": "date",
    "value date": "date",
    "transaction date": "date",
    "tran date": "date",
    "narration": "description",
    "description": "description",
    "particulars": "description",
    "details": "description",
    "remarks": "description",
    "transaction remarks": "description",
    "ref particulars": "description",
    "withdrawal": "debit",
    "debit": "debit",
    "dr": "debit",
    "withdrawal amt": "debit",
    "debit amount": "debit",
    "deposit": "credit",
    "credit": "credit",
    "cr": "credit",
    "deposit amt": "credit",
    "credit amount": "credit",
    "balance": "balance",
    "running balance": "balance",
    "closing balance": "balance",
    "available balance": "balance",
}

_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y",
    "%d/%m/%y", "%d-%m-%y",
    "%Y/%m/%d", "%Y-%m-%d",
    "%d %b %Y", "%d %b %y", "%d %B %Y",
    "%d-%b-%Y", "%d-%b-%y",
]


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

@dataclass
class TypeATransaction:
    """Normalized output of the TYPE_A parser."""
    date: str               # ISO  YYYY-MM-DD
    description: str
    debit: float | None
    credit: float | None
    balance: float | None
    raw_line: str = field(default="", repr=False)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _parse_date(raw: str) -> str | None:
    """Return ISO date string or None."""
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    # Try abbreviated month names capitalised
    for fmt in ("%d %B %Y", "%d %B %y"):
        try:
            return datetime.strptime(raw.title(), fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _clean_amount(raw: str | None) -> float | None:
    """Parse a monetary string into a positive float, or None."""
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    # Strip currency markers
    raw = re.sub(r"[₹$€£]|INR|Rs\.?", "", raw, flags=re.IGNORECASE).strip()
    # Parenthetical negative → still return positive (TYPE directs sign)
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()")
    raw = raw.replace(",", "")
    try:
        val = Decimal(raw)
        return float(abs(val))
    except InvalidOperation:
        return None


# ---------------------------------------------------------------------------
# Header detection
# ---------------------------------------------------------------------------

@dataclass
class _HeaderMap:
    date_idx: int
    desc_idx: int
    debit_idx: int | None
    credit_idx: int | None
    balance_idx: int | None
    # Character positions of each column start (for fixed-width PDFs)
    col_positions: list[int] = field(default_factory=list)


def _detect_header(lines: list[str], max_scan: int = 15) -> tuple[_HeaderMap | None, int]:
    """
    Scan up to `max_scan` lines for a header row.

    Returns (HeaderMap, line_index_of_header) or (None, -1).
    """
    for line_idx, line in enumerate(lines[:max_scan]):
        # Normalise to lowercase for matching
        low = line.lower()
        tokens = re.split(r"\s{2,}|\t", low)  # split on 2+ spaces or tab
        tokens_stripped = [t.strip() for t in tokens if t.strip()]

        # Map token → semantic column name
        col_map: dict[str, int] = {}
        for tok_idx, tok in enumerate(tokens_stripped):
            for keyword, semantic in _HEADER_KEYWORDS.items():
                if keyword in tok and semantic not in col_map:
                    col_map[semantic] = tok_idx
                    break

        if "date" in col_map and "description" in col_map and (
            "debit" in col_map or "credit" in col_map
        ):
            return _HeaderMap(
                date_idx=col_map["date"],
                desc_idx=col_map["description"],
                debit_idx=col_map.get("debit"),
                credit_idx=col_map.get("credit"),
                balance_idx=col_map.get("balance"),
            ), line_idx

    return None, -1


# ---------------------------------------------------------------------------
# Row parsing
# ---------------------------------------------------------------------------

def _split_row(line: str) -> list[str]:
    """Split a single table row on 2+ whitespace or tab, preserving order."""
    return [t for t in re.split(r"\s{2,}|\t", line) if t.strip()]


def _parse_row(tokens: list[str], hm: _HeaderMap, raw_line: str) -> TypeATransaction | None:
    """Map a list of tokens to a TypeATransaction using the header map."""
    if len(tokens) <= max(hm.date_idx, hm.desc_idx):
        return None

    date_str = _parse_date(tokens[hm.date_idx])
    if not date_str:
        return None

    desc = tokens[hm.desc_idx] if hm.desc_idx < len(tokens) else ""
    if not desc:
        return None

    if _SKIP_PAT.match(desc):
        return None

    debit = _clean_amount(tokens[hm.debit_idx]) if (hm.debit_idx is not None and hm.debit_idx < len(tokens)) else None
    credit = _clean_amount(tokens[hm.credit_idx]) if (hm.credit_idx is not None and hm.credit_idx < len(tokens)) else None
    balance = _clean_amount(tokens[hm.balance_idx]) if (hm.balance_idx is not None and hm.balance_idx < len(tokens)) else None

    # At least one of debit / credit must be present for a valid transaction
    if debit is None and credit is None:
        return None

    return TypeATransaction(
        date=date_str,
        description=desc[:255].strip(),
        debit=debit,
        credit=credit,
        balance=balance,
        raw_line=raw_line,
    )


# ---------------------------------------------------------------------------
# Continuation-row merging
# ---------------------------------------------------------------------------

def _is_continuation(line: str) -> bool:
    """Return True if the line looks like a continuation of the previous row."""
    tokens = _split_row(line)
    if not tokens:
        return False
    # A continuation row has no date in the first token
    first = tokens[0]
    if _DATE_PAT.search(first):
        return False
    # And no standalone monetary values (those would be a new txn)
    amounts = [t for t in tokens if _clean_amount(t) is not None]
    return len(amounts) == 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TypeAParser(BaseParser):
    """
    Parser for TYPE_A (structured table) bank statement text.
    """
    @property
    def name(self) -> str:
        return "type_a"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 30

    def can_handle(self, content: bytes, text: str, **kwargs: Any) -> float:
        if not text:
            return 0.0
        
        # Check for headers
        lines = text.splitlines()
        header, _ = _detect_header(lines)
        if header:
            return 0.95
            
        # Check for heuristic rows
        heuristic_rows = _heuristic_parse(lines[:100])
        if len(heuristic_rows) > 3:
            return 0.7
            
        return 0.1

    def parse(self, content: bytes, text: str, **kwargs: Any) -> ParserResponse:
        """
        Parse a TYPE_A bank statement text.
        """
        if not text:
            return ParserResponse(status="empty_text", transactions=[], reconciliation_score=0.0)

        raw_txns = parse_type_a(text)
        transactions = [
            ParsedTransaction(
                date=datetime.strptime(t.date, "%Y-%m-%d").date(),
                description=t.description,
                debit=t.debit,
                credit=t.credit,
                amount=t.debit if t.debit else t.credit,
                type="expense" if t.debit else "income",
                balance=t.balance,
            )
            for t in raw_txns
        ]

        return ParserResponse(
            status="success" if transactions else "no_transactions",
            reconciliation_score=1.0,
            transactions=transactions,
            meta={
                "parser_name": self.name,
                "parser_version": self.version,
                "count": len(transactions),
            }
        )

def parse_type_a(text: str) -> list[TypeATransaction]:
    """
    Parse a TYPE_A (structured table) bank statement text.

    Args:
        text: Raw multi-line text extracted from the PDF.

    Returns:
        List of TypeATransaction objects (invalid/noisy lines silently skipped).
    """
    if not text:
        return []

    lines = text.splitlines()
    header, header_idx = _detect_header(lines)

    if header is None:
        logger.warning("type_a_parser: no header row found, falling back to heuristic mode")
        # Still attempt parsing with positional guesses
        return _heuristic_parse(lines)

    transactions: list[TypeATransaction] = []
    pending_tx: TypeATransaction | None = None
    seen: set[tuple] = set()

    for line in lines[header_idx + 1:]:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        tokens = _split_row(line_stripped)
        if not tokens:
            continue

        # Check if this is a continuation of the previous transaction
        if pending_tx is not None and _is_continuation(line_stripped):
            # Append to description
            extra_desc = " ".join(t for t in tokens if _clean_amount(t) is None)
            if extra_desc:
                pending_tx.description = (pending_tx.description + " " + extra_desc).strip()[:255]
            continue

        # Emit previous transaction
        if pending_tx is not None:
            key = (pending_tx.date, pending_tx.description[:60].lower(), pending_tx.debit, pending_tx.credit)
            if key not in seen:
                seen.add(key)
                transactions.append(pending_tx)
        pending_tx = None

        # Try to parse as a new transaction row
        tx = _parse_row(tokens, header, line_stripped)
        if tx is not None:
            pending_tx = tx

    # Emit last pending
    if pending_tx is not None:
        key = (pending_tx.date, pending_tx.description[:60].lower(), pending_tx.debit, pending_tx.credit)
        if key not in seen:
            transactions.append(pending_tx)

    logger.info("type_a_parser: extracted %d transactions from %d lines", len(transactions), len(lines))
    return transactions


# ---------------------------------------------------------------------------
# Heuristic fallback (when no clean header is detected)
# ---------------------------------------------------------------------------

# A loose pattern: Date  [optional description text]  Amount  [DR|CR]  [Balance]
_LOOSE_ROW_PAT = re.compile(
    r"^(?P<date>\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2})"
    r"(?P<rest>.+)$",
    re.MULTILINE,
)

_TYPE_PAT = re.compile(r"\b(DR|CR|Debit|Credit|DEBIT|CREDIT)\b", re.IGNORECASE)


def _heuristic_parse(lines: list[str]) -> list[TypeATransaction]:
    """
    Loose row parsing when no header is detectable.
    Used as a last-resort inside TYPE_A parser.
    """
    results: list[TypeATransaction] = []
    seen: set[tuple] = set()

    for line in lines:
        m = _LOOSE_ROW_PAT.match(line.strip())
        if not m:
            continue

        date_str = _parse_date(m.group("date"))
        if not date_str:
            continue

        rest = m.group("rest").strip()
        if _SKIP_PAT.match(rest):
            continue

        # Extract type marker
        type_match = _TYPE_PAT.search(rest)
        tx_type = type_match.group(1).upper() if type_match else None
        if type_match:
            rest = rest[:type_match.start()] + rest[type_match.end():]

        # Extract all amounts
        amounts = [_clean_amount(t) for t in rest.split() if _clean_amount(t) is not None]
        amounts = [a for a in amounts if a is not None and a > 0]

        if not amounts:
            continue

        tx_amount = amounts[0]
        balance = amounts[-1] if len(amounts) > 1 else None

        # Derive description from non-amount, non-date tokens
        desc_tokens = [t for t in rest.split() if _clean_amount(t) is None]
        desc = " ".join(desc_tokens).strip()[:255] or "Transaction"

        debit = tx_amount if tx_type in ("DR", "DEBIT") else None
        credit = tx_amount if tx_type in ("CR", "CREDIT") else None

        if debit is None and credit is None:
            # Can't determine direction; skip
            continue

        key = (date_str, desc[:60].lower(), debit, credit)
        if key in seen:
            continue
        seen.add(key)

        results.append(TypeATransaction(
            date=date_str,
            description=desc,
            debit=debit,
            credit=credit,
            balance=balance,
            raw_line=line.strip(),
        ))

    logger.info("type_a_parser (heuristic): extracted %d rows", len(results))
    return results
