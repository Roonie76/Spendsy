"""
BankParserBase — abstract base class for all Indian bank statement parsers.

Subclasses must define:
  - COLUMN_SCHEMA  dict mapping field names → column indices
  - DATE_FORMATS   list of strptime format strings
  - bank_id        class-level string
  - identify()     → confidence float 0-1
  - extract_header() → AccountInfo
  - extract_table()  → list[BankTransaction]
  - extract_summary() → StatementSummary
"""
from __future__ import annotations

import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from app.postprocessing.date_normalizer import DateNormalizer
from app.postprocessing.amount_cleaner import AmountCleaner
from app.postprocessing.transaction_type import TransactionTypeClassifier

logger = logging.getLogger(__name__)


# ── Output data models ──────────────────────────────────────────────────────

@dataclass
class AccountInfo:
    account_number: str | None = None
    account_holder: str | None = None
    ifsc_code:      str | None = None
    branch:         str | None = None
    bank_name:      str | None = None
    account_type:   str | None = None
    statement_from: date | None = None
    statement_to:   date | None = None
    currency:       str = "INR"


@dataclass
class BankTransaction:
    date:             date
    description:      str
    debit:            Decimal | None = None
    credit:           Decimal | None = None
    balance:          Decimal | None = None
    value_date:       date | None = None
    reference_no:     str | None = None
    transaction_type: str = "OTHERS"
    confidence:       float = 1.0
    page_number:      int = 0
    raw_row:          str = ""


@dataclass
class StatementSummary:
    opening_balance:   Decimal | None = None
    closing_balance:   Decimal | None = None
    total_debits:      Decimal | None = None
    total_credits:     Decimal | None = None
    transaction_count: int = 0


# ── Summary patterns — rows to skip ─────────────────────────────────────────

SUMMARY_SKIP_PATTERNS = [
    re.compile(r"^\s*(opening|closing)\s+balance\b", re.IGNORECASE),
    re.compile(r"^\s*(b/f|brought\s+forward)\b", re.IGNORECASE),
    re.compile(r"^\s*total\s+(debit|credit|withdraw|deposit|txn|transactions)\b", re.IGNORECASE),
]


def _is_summary_row(text: str) -> bool:
    return any(p.search(text) for p in SUMMARY_SKIP_PATTERNS)


# ── Base class ───────────────────────────────────────────────────────────────

class BankParserBase(ABC):

    # Subclasses override these
    bank_id: str = "GENERIC"
    DATE_FORMATS: list[str] = []
    COLUMN_SCHEMA: dict[str, int | None] = {}

    @abstractmethod
    def identify(self, probe_text: str) -> float:
        """Return a confidence score 0-1 that this parser handles the given text."""

    @abstractmethod
    def extract_header(self, all_pages: list) -> AccountInfo:
        """Extract account metadata from page data list."""

    @abstractmethod
    def extract_table(self, all_pages: list) -> list[BankTransaction]:
        """Extract all transactions from page data list."""

    @abstractmethod
    def extract_summary(self, all_pages: list) -> StatementSummary:
        """Extract opening/closing balance and totals."""

    # ── Shared utilities ────────────────────────────────────────────────────

    def _pages_text(self, all_pages: list, n: int = 2) -> str:
        return "\n".join(getattr(p, "raw_text", "") for p in all_pages[:n])

    def _all_text(self, all_pages: list) -> str:
        return "\n".join(getattr(p, "raw_text", "") for p in all_pages)

    def _find_header_value(self, text: str, patterns: list[str]) -> str | None:
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return None

    def _find_data_start(self, table: list[list[str]], date_kw: str = "DATE") -> int:
        for i, row in enumerate(table):
            joined = " ".join(row).upper()
            if date_kw in joined and any(k in joined for k in ("AMOUNT", "DEBIT", "CREDIT", "BALANCE", "NARRATION", "DESCRIPTION")):
                return i + 1
        return 0

    def _merge_multiline_rows(self, rows: list[list[str]], date_col: int = 0, desc_col: int = 1) -> list[list[str]]:
        merged: list[list[str]] = []
        dn = DateNormalizer(self.DATE_FORMATS or None)
        current: list[str] | None = None

        for row in rows:
            date_cell = row[date_col].strip() if date_col < len(row) else ""
            if dn.is_valid(date_cell):
                if current is not None:
                    merged.append(current)
                current = list(row)
            elif current is not None and desc_col < len(row):
                # continuation line — append narration text
                extra = row[desc_col].strip() if desc_col < len(row) else ""
                if extra and desc_col < len(current):
                    current[desc_col] = (current[desc_col] + " " + extra).strip()
        if current is not None:
            merged.append(current)
        return merged

    def _row_to_transaction(self, row: list[str], page_number: int = 0) -> BankTransaction | None:
        schema = self.COLUMN_SCHEMA
        dn     = DateNormalizer(self.DATE_FORMATS or None)

        date_raw = self._cell(row, schema.get("date"))
        tx_date  = dn.parse(date_raw)
        if tx_date is None:
            return None

        desc_raw = self._cell(row, schema.get("description"))
        if not desc_raw or _is_summary_row(desc_raw):
            return None

        debit   = AmountCleaner.parse(self._cell(row, schema.get("debit")))
        credit  = AmountCleaner.parse(self._cell(row, schema.get("credit")))
        balance = AmountCleaner.parse(self._cell(row, schema.get("balance")))
        ref_no  = self._cell(row, schema.get("ref_no")) or None
        val_dt  = dn.parse(self._cell(row, schema.get("value_date")))

        # Single amount column + dr/cr flag
        if "amount" in schema and schema["amount"] is not None:
            amt  = AmountCleaner.parse(self._cell(row, schema["amount"]))
            flag = self._cell(row, schema.get("dr_cr_flag", None)).upper()
            if amt is not None:
                if "DR" in flag or flag == "D":
                    debit = amt; credit = None
                else:
                    credit = amt; debit = None

        tx_type = TransactionTypeClassifier.classify(desc_raw)

        return BankTransaction(
            date=tx_date,
            description=desc_raw[:255],
            debit=debit,
            credit=credit,
            balance=balance,
            value_date=val_dt,
            reference_no=ref_no,
            transaction_type=tx_type,
            confidence=1.0,
            page_number=page_number,
            raw_row="|".join(row),
        )

    def _rows_to_transactions(self, rows: list[list[str]], page_number: int = 0) -> list[BankTransaction]:
        txns = []
        for row in rows:
            try:
                tx = self._row_to_transaction(row, page_number)
                if tx:
                    txns.append(tx)
            except Exception as e:
                logger.debug("_row_to_transaction skip: %s | row=%s", e, row)
        return txns

    @staticmethod
    def _cell(row: list[str], idx: int | None) -> str:
        if idx is None or idx >= len(row):
            return ""
        return (row[idx] or "").strip()
