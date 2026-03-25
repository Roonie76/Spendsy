"""
GenericParser — auto-detects column schema from header row.
Regex-driven fallback for unknown banks. Always returns low identify() confidence.
"""
from __future__ import annotations
import re
import logging
from app.parsers.banks.base import BankParserBase, AccountInfo, BankTransaction, StatementSummary
from app.postprocessing.amount_cleaner import AmountCleaner
from app.postprocessing.date_normalizer import DateNormalizer

logger = logging.getLogger(__name__)

# Column header alias groups
_COL_ALIASES: dict[str, list[str]] = {
    "date":        ["TXN DATE", "TRANSACTION DATE", "DATE", "POST DATE", "VALUE DATE"],
    "description": ["NARRATION", "DESCRIPTION", "PARTICULARS", "REMARKS", "DETAILS", "TRANSACTION REMARKS"],
    "debit":       ["WITHDRAWAL", "DEBIT", "DR", "DR AMOUNT", "PAID OUT", "WITHDRAWAL AMT", "DEBIT AMOUNT"],
    "credit":      ["DEPOSIT", "CREDIT", "CR", "CR AMOUNT", "PAID IN", "DEPOSIT AMT", "CREDIT AMOUNT"],
    "balance":     ["BALANCE", "CLOSING BALANCE", "RUNNING BALANCE", "AVAILABLE BALANCE"],
    "ref_no":      ["REF", "REFERENCE", "CHQ NO", "CHEQUE", "REF NO", "REF NO/CHEQUE NO"],
    "value_date":  ["VALUE DATE", "VALUE DT"],
}


def _auto_detect_schema(header_row: list[str]) -> dict[str, int | None]:
    schema: dict[str, int | None] = {k: None for k in _COL_ALIASES}
    normalised = [h.strip().upper() for h in header_row]
    date_hits = 0
    for i, header in enumerate(normalised):
        for field, aliases in _COL_ALIASES.items():
            if schema[field] is not None:
                continue  # already assigned
            if any(alias in header for alias in aliases):
                if field == "date":
                    if date_hits == 0:
                        schema["date"] = i
                    else:
                        schema["value_date"] = i
                    date_hits += 1
                else:
                    schema[field] = i
    return schema


class GenericParser(BankParserBase):
    bank_id      = "GENERIC"
    DATE_FORMATS = []  # will try all formats

    def identify(self, probe_text: str) -> float:
        return 0.1  # always lowest priority

    def extract_header(self, all_pages: list) -> AccountInfo:
        text = self._pages_text(all_pages)
        return AccountInfo(
            bank_name      = "Unknown",
            account_number = self._find_header_value(text, [
                r"[Aa]ccount\s*[Nn]o\.?\s*[:\-]?\s*(\d{9,18})",
                r"A/[Cc]\s*[Nn]o\.?\s*[:\-]?\s*(\d{9,18})",
            ]),
            account_holder = self._find_header_value(text, [r"[Nn]ame\s*[:\-]\s*([A-Z][A-Za-z\s\.]+)\n"]),
            ifsc_code      = self._find_header_value(text, [r"IFSC\s*[:\-]?\s*([A-Z]{4}0[A-Z0-9]{6})"]),
        )

    def extract_table(self, all_pages: list) -> list[BankTransaction]:
        all_txns: list[BankTransaction] = []
        for page in all_pages:
            for table in getattr(page, "tables", []):
                header_idx = self._find_header_row_idx(table)
                if header_idx is None:
                    continue
                schema = _auto_detect_schema(table[header_idx])
                if schema.get("date") is None or schema.get("balance") is None:
                    continue
                # Temporarily apply detected schema
                self.COLUMN_SCHEMA = schema
                self.DATE_FORMATS  = []
                rows = self._merge_multiline_rows(
                    table[header_idx + 1:],
                    date_col=schema["date"],
                    desc_col=schema.get("description") or 1,
                )
                all_txns.extend(self._rows_to_transactions(rows, page.page_number))
        return all_txns

    def extract_summary(self, all_pages: list) -> StatementSummary:
        text = self._all_text(all_pages)
        return StatementSummary(
            opening_balance = AmountCleaner.parse(self._find_header_value(text, [r"Opening\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
            closing_balance = AmountCleaner.parse(self._find_header_value(text, [r"Closing\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
        )

    def _find_header_row_idx(self, table: list[list[str]]) -> int | None:
        for i, row in enumerate(table[:6]):
            joined = " ".join(row).upper()
            if "DATE" in joined and ("BALANCE" in joined or "DEBIT" in joined or "CREDIT" in joined):
                return i
        return None
