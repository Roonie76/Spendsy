"""
HDFCParser — handles HDFC Bank statement PDFs.

HDFC standard column order:
  Date | Narration | Chq/Ref No | Value Dt | Withdrawal Amt | Deposit Amt | Closing Balance
"""
from __future__ import annotations
import re
from decimal import Decimal
from app.parsers.banks.base import BankParserBase, AccountInfo, BankTransaction, StatementSummary
from app.postprocessing.amount_cleaner import AmountCleaner


class HDFCParser(BankParserBase):
    bank_id       = "HDFC"
    DATE_FORMATS  = ["%d/%m/%y", "%d/%m/%Y", "%d-%m-%Y"]
    COLUMN_SCHEMA = {
        "date": 0, "description": 1, "ref_no": 2,
        "value_date": 3, "debit": 4, "credit": 5, "balance": 6,
    }

    def identify(self, probe_text: str) -> float:
        upper = probe_text.upper()
        score = 0.0
        if "HDFC BANK" in upper:         score += 0.5
        if "WITHDRAWAL AMT" in upper:    score += 0.3
        if "DEPOSIT AMT" in upper:       score += 0.2
        return min(score, 1.0)

    def extract_header(self, all_pages: list) -> AccountInfo:
        text = self._pages_text(all_pages)
        return AccountInfo(
            bank_name      = "HDFC Bank",
            account_number = self._find_header_value(text, [
                r"A/c?\s*No\.?\s*[:\-]\s*([\d\s]{10,18})",
                r"Account\s*No\.?\s*[:\-]\s*(\d{10,16})",
            ]),
            account_holder = self._find_header_value(text, [
                r"(?:MR|MRS|MS|DR)\.?\s+([A-Z][A-Z\s\.]{2,40})\n",
                r"Name\s*[:\-]\s*(.+)\n",
            ]),
            ifsc_code      = self._find_header_value(text, [r"IFSC\s*[:\-]\s*([A-Z]{4}0[A-Z0-9]{6})"]),
            branch         = self._find_header_value(text, [r"Branch\s*[:\-]\s*(.+)\n"]),
            statement_from = self._find_date(text, r"From\s*[:\-]\s*(\d{2}/\d{2}/\d{4})"),
            statement_to   = self._find_date(text, r"To\s*[:\-]\s*(\d{2}/\d{2}/\d{4})"),
        )

    def extract_table(self, all_pages: list) -> list[BankTransaction]:
        all_txns: list[BankTransaction] = []
        for page in all_pages:
            for table in getattr(page, "tables", []):
                start = self._find_data_start(table)
                rows  = self._merge_multiline_rows(table[start:], date_col=0, desc_col=1)
                all_txns.extend(self._rows_to_transactions(rows, page.page_number))
        return all_txns

    def extract_summary(self, all_pages: list) -> StatementSummary:
        text = self._all_text(all_pages)
        return StatementSummary(
            opening_balance = AmountCleaner.parse(self._find_header_value(text, [r"Opening\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
            closing_balance = AmountCleaner.parse(self._find_header_value(text, [r"Closing\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
        )

    def _find_date(self, text: str, pattern: str):
        from app.postprocessing.date_normalizer import DateNormalizer
        v = self._find_header_value(text, [pattern])
        return DateNormalizer(self.DATE_FORMATS).parse(v) if v else None
