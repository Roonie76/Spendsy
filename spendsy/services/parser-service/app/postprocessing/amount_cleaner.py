"""
AmountCleaner — safely parses bank amount strings into Decimal.
Handles currency symbols, thousands separators, bracketed negatives, Dr/Cr suffixes.
"""
from __future__ import annotations

import re
import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

_CURRENCY_RE = re.compile(r"[₹$£€]")
_DR_CR_SUFFIX = re.compile(r"\s*(DR|CR|D|C)$", re.IGNORECASE)
_WHITESPACE_IN_NUM = re.compile(r"(?<=\d)\s+(?=\d)")


class AmountCleaner:
    @staticmethod
    def parse(raw: str | None) -> Decimal | None:
        """
        Parse a raw amount string to Decimal.
        Returns None if the string is empty or unparseable.
        Negative amounts are returned as negative Decimal values.
        """
        if not raw:
            return None

        s = raw.strip()
        if not s:
            return None

        # Remove currency symbols
        s = _CURRENCY_RE.sub("", s).strip()
        s = re.sub(r"\bINR\b|\bRS\.?\b", "", s, flags=re.IGNORECASE).strip()

        # Strip Dr/Cr suffix and remember is_debit
        is_debit = False
        m = _DR_CR_SUFFIX.search(s)
        if m:
            suffix = m.group(1).upper()
            is_debit = suffix in ("DR", "D")
            s = s[: m.start()].strip()

        # Handle bracketed negatives: (1,200.00) → -1200.00
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]

        # Remove thousand separators and internal spaces between digits
        s = s.replace(",", "")
        s = _WHITESPACE_IN_NUM.sub("", s)

        try:
            value = Decimal(s)
        except (InvalidOperation, ValueError):
            logger.debug("AmountCleaner: cannot parse '%s'", raw)
            return None

        # If Dr suffix was present and the value is positive, flip sign
        if is_debit and value > 0:
            value = -value

        return value

    @staticmethod
    def to_float(raw: str | None) -> float | None:
        d = AmountCleaner.parse(raw)
        return float(d) if d is not None else None
