"""
TYPE_B Parser — DR/CR indicator format for SBI, PNB, Canara, BOB and other PSU banks.

In this format transactions look like:

    28/11/2025  270.00  DR  237.55  NEFT TRANSFER REF 12345
    30/11/2025  500.00  CR  737.55  SALARY CREDIT

The key difference from TYPE_A:
    - A single "Amount" column is used (not split into Debit/Credit columns)
    - A "DR" or "CR" marker adjacent to the amount indicates direction
    - The marker can appear BEFORE or AFTER the amount

Parsing strategy:
    1. Scan for header to locate column positions
    2. If no clean header, use the strict inline regex approach
    3. Parse each row: extract date → amount → DR/CR marker → balance → description
    4. Convert DR/CR to debit/credit fields
    5. Dedup and return TypeBTransaction list
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.base_parser import BaseParser
from app.core.schemas import ParsedTransaction, ParserResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Matches: Date  Amount  DR/CR  Balance  Description
# or:      Date  Amount(DR)  Balance  Description
_STRICT_ROW_PAT = re.compile(
    r"^(?P<date>\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2})\s+"
    r"(?P<amount>[\d,.]+(?:\.\d{1,2})?)\s+"
    r"(?P<type>DR|CR|Debit|Credit|DEBIT|CREDIT|D|C)\s+"
    r"(?P<balance>[\d,.]+(?:\.\d{1,2})?)\s+"
    r"(?P<desc>.+)$",
    re.IGNORECASE,
)

# Loose pattern — amount THEN marker THEN balance, description anywhere
_LOOSE_ROW_PAT = re.compile(
    r"^(?P<date>\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\d{4}[/\-]\d{2}[/\-]\d{2})"
    r"(?P<rest>.+)$",
    re.MULTILINE,
)

_TYPE_PAT = re.compile(r"\b(?P<marker>DR|CR|Debit|Credit|DEBIT|CREDIT|D|C)\b", re.IGNORECASE)

_AMOUNT_RE = re.compile(
    r"(?:[₹$]|INR|Rs\.?)?\s*(?P<val>(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d{1,2})?)"
)

_SKIP_PAT = re.compile(
    r"^\s*(?:opening|closing|total|b/f|brought\s+forward|available"
    r"|statement\s+date|account\s+(?:no|number)|page\s+\d|date\s+(?:desc|narr)|balance\s+b/f)",
    re.IGNORECASE,
)

_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y",
    "%d/%m/%y", "%d-%m-%y",
    "%Y/%m/%d", "%Y-%m-%d",
    "%d %b %Y", "%d %b %y", "%d %B %Y",
    "%d-%b-%Y",
]


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

@dataclass
class TypeBTransaction:
    """Normalized output of the TYPE_B parser."""
    date: str               # ISO YYYY-MM-DD
    description: str
    debit: float | None     # populated when marker is DR
    credit: float | None    # populated when marker is CR
    balance: float | None
    raw_line: str = field(default="", repr=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(raw: str) -> str | None:
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _clean_amount(raw: str | None) -> float | None:
    if not raw:
        return None
    raw = re.sub(r"[₹$€£]|INR|Rs\.?", "", raw, flags=re.IGNORECASE).strip()
    raw = raw.replace(",", "")
    try:
        return float(abs(Decimal(raw)))
    except InvalidOperation:
        return None


def _extract_amounts(text: str) -> list[float]:
    """Extract all valid numeric amounts from a string."""
    results = []
    for m in _AMOUNT_RE.finditer(text):
        val = _clean_amount(m.group("val"))
        if val is not None and val > 0:
            results.append(val)
    return results


def _classify_marker(marker: str) -> str:
    """Normalize DR/CR marker to 'DR' or 'CR'."""
    m = marker.strip().upper()
    if m in ("DR", "D", "DEBIT"):
        return "DR"
    if m in ("CR", "C", "CREDIT"):
        return "CR"
    return m


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TypeBParser(BaseParser):
    """
    Parser for TYPE_B (DR/CR indicator format) bank statement text.
    """
    @property
    def name(self) -> str:
        return "type_b"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 35

    def can_handle(self, content: bytes, text: str, **kwargs: Any) -> float:
        if not text:
            return 0.0
            
        # Check for DR/CR markers
        # Note: _TYPE_PAT is defined at the module level
        dr_cr_count = len(re.findall(r"\b(DR|CR|Debit|Credit|DEBIT|CREDIT|D|C)\b", text, re.IGNORECASE))
        
        # Sample rows check
        lines = text.splitlines()[:50]
        valid = sum(1 for l in lines if _try_strict(l) or _try_loose(l))
        
        score = 0.0
        if dr_cr_count > 10:
            score += 0.4
        if valid > 5:
            score += 0.5
            
        return min(score, 0.95)

    def parse(self, content: bytes, text: str, **kwargs: Any) -> ParserResponse:
        """
        Parse a TYPE_B bank statement text.
        """
        if not text:
            return ParserResponse(status="empty_text", transactions=[], reconciliation_score=0.0)

        raw_txns = parse_type_b(text)
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

def parse_type_b(text: str) -> list[TypeBTransaction]:
    """
    Parse a TYPE_B (DR/CR indicator format) bank statement text.

    Args:
        text: Raw multi-line text from the PDF.

    Returns:
        List of TypeBTransaction objects. Lines that fail to parse are skipped.
    """
    if not text:
        return []

    lines = text.splitlines()
    transactions: list[TypeBTransaction] = []
    seen: set[tuple] = set()

    for line in lines:
        line = line.strip()
        if not line or _SKIP_PAT.match(line):
            continue

        tx = _try_strict(line) or _try_loose(line)
        if tx is None:
            continue

        key = (tx.date, tx.description[:60].lower(), tx.debit, tx.credit)
        if key in seen:
            logger.debug("type_b_parser: duplicate skipped date=%s", tx.date)
            continue
        seen.add(key)
        transactions.append(tx)

    logger.info("type_b_parser: extracted %d transactions from %d lines", len(transactions), len(lines))
    return transactions


# ---------------------------------------------------------------------------
# Strategy 1: Strict regex (most reliable)
# ---------------------------------------------------------------------------

def _try_strict(line: str) -> TypeBTransaction | None:
    """
    Attempt to parse using the strict pattern:
        Date  Amount  DR/CR  Balance  Description
    """
    m = _STRICT_ROW_PAT.match(line)
    if not m:
        return None

    date_str = _parse_date(m.group("date"))
    if not date_str:
        return None

    raw_amount = _clean_amount(m.group("amount"))
    if raw_amount is None or raw_amount <= 0:
        return None

    marker = _classify_marker(m.group("type"))
    balance = _clean_amount(m.group("balance"))
    desc = m.group("desc").strip()[:255] or "Transaction"

    if _SKIP_PAT.match(desc):
        return None

    debit = raw_amount if marker == "DR" else None
    credit = raw_amount if marker == "CR" else None

    return TypeBTransaction(
        date=date_str,
        description=desc,
        debit=debit,
        credit=credit,
        balance=balance,
        raw_line=line,
    )


# ---------------------------------------------------------------------------
# Strategy 2: Loose heuristic parsing
# ---------------------------------------------------------------------------

def _try_loose(line: str) -> TypeBTransaction | None:
    """
    Heuristic parsing for rows where the column order is not perfectly known.
    Finds date → extracts all amounts → finds DR/CR → assigns accordingly.
    """
    m = _LOOSE_ROW_PAT.match(line)
    if not m:
        return None

    date_str = _parse_date(m.group("date"))
    if not date_str:
        return None

    rest = m.group("rest").strip()
    if _SKIP_PAT.match(rest):
        return None

    # Find the DR/CR marker
    type_match = _TYPE_PAT.search(rest)
    if not type_match:
        # No DR/CR at all → cannot classify direction safely → skip
        return None

    marker = _classify_marker(type_match.group("marker"))

    # Remove the marker from rest to isolate amounts + description
    rest_no_marker = rest[: type_match.start()] + rest[type_match.end():]

    amounts = _extract_amounts(rest_no_marker)
    if not amounts:
        return None

    # Heuristic: smallest amount = transaction, largest = balance (if different)
    amounts_sorted = sorted(amounts)
    tx_amount = amounts_sorted[0]
    balance = amounts_sorted[-1] if len(amounts_sorted) > 1 else None

    # Build description from non-amount tokens
    desc_tokens = [
        t for t in rest_no_marker.split()
        if _clean_amount(t) is None
    ]
    desc = " ".join(desc_tokens).strip()[:255] or "Transaction"

    if _SKIP_PAT.match(desc):
        return None

    debit = tx_amount if marker == "DR" else None
    credit = tx_amount if marker == "CR" else None

    return TypeBTransaction(
        date=date_str,
        description=desc,
        debit=debit,
        credit=credit,
        balance=balance,
        raw_line=line,
    )
