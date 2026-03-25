"""
AxisParser, KotakParser — handles Axis Bank and Kotak Mahindra Bank statements.
Both use a similar 6-column format:
  Date | Description | Chq/Ref | Debit | Credit | Balance
"""
from __future__ import annotations
import re
from app.parsers.banks.base import BankParserBase, AccountInfo, BankTransaction, StatementSummary
from app.postprocessing.amount_cleaner import AmountCleaner


class AxisParser(BankParserBase):
    bank_id       = "AXIS"
    DATE_FORMATS  = ["%d-%m-%Y", "%d/%m/%Y", "%d/%m/%y"]
    COLUMN_SCHEMA = {
        "date": 0, "description": 1, "ref_no": 2,
        "debit": 3, "credit": 4, "balance": 5,
    }

    def identify(self, probe_text: str) -> float:
        upper = probe_text.upper()
        score = 0.0
        if "AXIS BANK" in upper:                    score += 0.5
        if re.search(r"UTIB0\d{6}", probe_text):    score += 0.4
        if "AXISBANK.COM" in upper:                 score += 0.1
        return min(score, 1.0)

    def extract_header(self, all_pages: list) -> AccountInfo:
        text = self._pages_text(all_pages)
        return AccountInfo(
            bank_name      = "Axis Bank",
            account_number = self._find_header_value(text, [r"Account\s*(?:No\.?|Number)\s*[:\-]\s*(\d{9,18})"]),
            account_holder = self._find_header_value(text, [r"(?:Name|Customer)\s*[:\-]\s*(.+)\n"]),
            ifsc_code      = self._find_header_value(text, [r"(UTIB0[A-Z0-9]{6})"]),
        )

    def extract_table(self, all_pages: list) -> list[BankTransaction]:
        all_txns: list[BankTransaction] = []
        for page in all_pages:
            for table in getattr(page, "tables", []):
                start = self._find_data_start(table)
                rows  = self._merge_multiline_rows(table[start:])
                all_txns.extend(self._rows_to_transactions(rows, page.page_number))
        return all_txns

    def extract_summary(self, all_pages: list) -> StatementSummary:
        text = self._all_text(all_pages)
        return StatementSummary(
            opening_balance = AmountCleaner.parse(self._find_header_value(text, [r"Opening\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
            closing_balance = AmountCleaner.parse(self._find_header_value(text, [r"Closing\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
        )


class KotakParser(BankParserBase):
    bank_id       = "KOTAK"
    DATE_FORMATS  = ["%d-%m-%Y", "%d/%m/%Y", "%d %b %Y"]
    COLUMN_SCHEMA = {
        "date": 0, "description": 1, "ref_no": 2,
        "debit": 3, "credit": 4, "balance": 5,
    }

    def identify(self, probe_text: str) -> float:
        upper = probe_text.upper()
        score = 0.0
        if "KOTAK" in upper:                        score += 0.5
        if re.search(r"KKBK0\d{6}", probe_text):    score += 0.4
        if "KOTAK.COM" in upper:                    score += 0.1
        return min(score, 1.0)

    def extract_header(self, all_pages: list) -> AccountInfo:
        text = self._pages_text(all_pages)
        return AccountInfo(
            bank_name      = "Kotak Mahindra Bank",
            account_number = self._find_header_value(text, [r"Account\s*(?:No\.?|Number)\s*[:\-]\s*(\d{9,16})"]),
            account_holder = self._find_header_value(text, [r"Name\s*[:\-]\s*(.+)\n"]),
            ifsc_code      = self._find_header_value(text, [r"(KKBK0[A-Z0-9]{6})"]),
        )

    def extract_table(self, all_pages: list) -> list[BankTransaction]:
        all_txns: list[BankTransaction] = []
        for page in all_pages:
            for table in getattr(page, "tables", []):
                start = self._find_data_start(table)
                rows  = self._merge_multiline_rows(table[start:])
                all_txns.extend(self._rows_to_transactions(rows, page.page_number))
        return all_txns

    def extract_summary(self, all_pages: list) -> StatementSummary:
        text = self._all_text(all_pages)
        return StatementSummary(
            opening_balance = AmountCleaner.parse(self._find_header_value(text, [r"Opening\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
            closing_balance = AmountCleaner.parse(self._find_header_value(text, [r"Closing\s*Balance\s*[:\-]?\s*([\d,]+\.\d{2})"])),
        )
