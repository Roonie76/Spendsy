"""
ICICIParser — handles ICICI Bank / iMobile statement PDFs.

ICICI column order:
  S No | Transaction Date | Value Date | Transaction Remarks |
  Ref No/Cheque No | Withdrawal Amount | Deposit Amount | Balance
"""
from __future__ import annotations
import re
from app.parsers.banks.base import BankParserBase, AccountInfo, BankTransaction, StatementSummary
from app.postprocessing.amount_cleaner import AmountCleaner


class ICICIParser(BankParserBase):
    bank_id       = "ICICI"
    DATE_FORMATS  = ["%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"]
    COLUMN_SCHEMA = {
        "date": 1, "value_date": 2, "description": 3,
        "ref_no": 4, "debit": 5, "credit": 6, "balance": 7,
    }

    def identify(self, probe_text: str) -> float:
        upper = probe_text.upper()
        score = 0.0
        if "ICICI BANK" in upper:            score += 0.5
        if "TRANSACTION REMARKS" in upper:   score += 0.3
        if re.search(r"ICIC0\d{6}", probe_text): score += 0.2
        return min(score, 1.0)

    def extract_header(self, all_pages: list) -> AccountInfo:
        text = self._pages_text(all_pages)
        return AccountInfo(
            bank_name      = "ICICI Bank",
            account_number = self._find_header_value(text, [
                r"Account\s*No\.?\s*[:\-]\s*(\d{12,16})",
            ]),
            account_holder = self._find_header_value(text, [r"Name\s*[:\-]\s*(.+)\n"]),
            ifsc_code      = self._find_header_value(text, [r"(ICIC0\d{6})"]),
        )

    def extract_table(self, all_pages: list) -> list[BankTransaction]:
        all_txns: list[BankTransaction] = []
        for page in all_pages:
            for table in getattr(page, "tables", []):
                start = self._find_data_start(table)
                rows  = self._merge_multiline_rows(table[start:], date_col=1, desc_col=3)
                all_txns.extend(self._rows_to_transactions(rows, page.page_number))
        return all_txns

    def extract_summary(self, all_pages: list) -> StatementSummary:
        text = self._all_text(all_pages)
        return StatementSummary(
            opening_balance = AmountCleaner.parse(self._find_header_value(text, [r"Opening\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
            closing_balance = AmountCleaner.parse(self._find_header_value(text, [r"Closing\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
        )
