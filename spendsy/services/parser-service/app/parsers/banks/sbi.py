"""
SBIParser — handles State Bank of India statement PDFs.

SBI column order (YONO exports and branch printouts):
  Txn Date | Value Date | Description | Ref No/Cheque No | Debit | Credit | Balance
"""
from __future__ import annotations
from app.parsers.banks.base import BankParserBase, AccountInfo, BankTransaction, StatementSummary
from app.postprocessing.amount_cleaner import AmountCleaner


class SBIParser(BankParserBase):
    bank_id       = "SBI"
    DATE_FORMATS  = ["%d %b %Y", "%d-%m-%Y", "%d/%m/%Y", "%d/%m/%y"]
    COLUMN_SCHEMA = {
        "date": 0, "value_date": 1, "description": 2,
        "ref_no": 3, "debit": 4, "credit": 5, "balance": 6,
    }

    def identify(self, probe_text: str) -> float:
        upper = probe_text.upper()
        score = 0.0
        if "STATE BANK OF INDIA" in upper: score += 0.6
        if "YONO" in upper:               score += 0.1
        if re.search(r"SBIN0[A-Z0-9]{6}", probe_text): score += 0.3
        return min(score, 1.0)

    def extract_header(self, all_pages: list) -> AccountInfo:
        text = self._pages_text(all_pages)
        return AccountInfo(
            bank_name      = "State Bank of India",
            account_number = self._find_header_value(text, [
                r"Account\s*Number\s*[:\-]\s*(\d{11,17})",
                r"A/C\s*No\s*[:\-]\s*(\d{9,17})",
            ]),
            account_holder = self._find_header_value(text, [
                r"Account\s*Name\s*[:\-]\s*(.+)\n",
                r"Name\s*[:\-]\s*(.+)\n",
            ]),
            ifsc_code = self._find_header_value(text, [r"(SBIN0[A-Z0-9]{6})"]),
            branch    = self._find_header_value(text, [r"Branch\s*(?:Name)?\s*[:\-]\s*(.+)\n"]),
        )

    def extract_table(self, all_pages: list) -> list[BankTransaction]:
        all_txns: list[BankTransaction] = []
        for page in all_pages:
            for table in getattr(page, "tables", []):
                start = self._find_data_start(table, date_kw="DATE")
                rows  = self._merge_multiline_rows(table[start:], date_col=0, desc_col=2)
                all_txns.extend(self._rows_to_transactions(rows, page.page_number))
        return all_txns

    def extract_summary(self, all_pages: list) -> StatementSummary:
        text = self._all_text(all_pages)
        return StatementSummary(
            opening_balance = AmountCleaner.parse(self._find_header_value(text, [r"Opening\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
            closing_balance = AmountCleaner.parse(self._find_header_value(text, [r"Closing\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
        )

import re
