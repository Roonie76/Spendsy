from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

import pdfplumber
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

try:
    import polars as pl
except Exception:  # pragma: no cover
    pl = None  # type: ignore[assignment]

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore[assignment]

DATE_CANDIDATE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
AMOUNT_CANDIDATE = re.compile(r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?")
OCR_NUMERIC = re.compile(r"\d+\.\d{2}")
SUMMARY_MARKERS = ("opening balance", "closing balance", "total", "summary", "b/f", "brought forward")


class ParsedTransaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    description: str
    amount: float
    type: Literal["income", "expense"]
    balance: float | None = None
    is_valid: bool = True


class ParserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    reconciliation_score: float
    transactions: list[ParsedTransaction]
    meta: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class _HeaderMap:
    date_idx: int
    desc_idx: int
    debit_idx: int | None
    credit_idx: int | None
    amount_idx: int | None
    balance_idx: int | None


class IntegratedParser:
    def __init__(self) -> None:
        pass

    def parse(self, pdf_bytes: bytes) -> ParserResponse:
        digital_rows = self._extract_digital(pdf_bytes)
        method = "digital"
        if not digital_rows:
            method = "ocr"
            digital_rows = self._extract_ocr(pdf_bytes)

        cleaned = self._clean_with_polars(digital_rows)
        reconciled, score = self.verify_integrity(cleaned)
        ordered = sorted(
            reconciled,
            key=lambda t: (t.date.isoformat(), t.description.lower(), round(float(t.amount), 2), t.type),
        )
        return ParserResponse(
            status="success" if ordered else "no_transactions",
            reconciliation_score=round(score, 4),
            transactions=ordered,
            meta={
                "method": method,
                "checksum_verified": bool(score >= 0.9 if ordered else True),
                "count": len(ordered),
            },
        )

    def _extract_digital(self, pdf_bytes: bytes) -> list[ParsedTransaction]:
        transactions: list[ParsedTransaction] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_idx, page in enumerate(pdf.pages):
                tables = page.extract_tables() or []
                logger.info("parser_stage=digital_extract page=%d tables_found=%d", page_idx + 1, len(tables))
                for table in tables:
                    if not table:
                        continue
                    header = self._detect_header(table)
                    if header is None:
                        continue
                    for row in table[1:]:
                        tx = self._parse_table_row(row, header)
                        if tx is not None:
                            transactions.append(tx)
        logger.info("parser_stage=digital_parse transactions=%d", len(transactions))
        return transactions

    def _extract_ocr(self, pdf_bytes: bytes) -> list[ParsedTransaction]:
        if pytesseract is None:
            logger.warning("parser_stage=ocr_extract skipped=missing_pytesseract")
            return []

        lines: list[str] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_idx, page in enumerate(pdf.pages[:10]):
                image = page.to_image(resolution=220).original
                text = pytesseract.image_to_string(image, config="--oem 3 --psm 6")
                page_lines = [self._normalize_cell(x) for x in text.splitlines() if self._normalize_cell(x)]
                logger.info("parser_stage=ocr_extract page=%d lines=%d", page_idx + 1, len(page_lines))
                lines.extend(page_lines)

        items, skipped, valid = self._parse_ocr_lines(lines)
        logger.info(
            "parser_stage=ocr_parse total_lines=%d valid_rows=%d skipped_rows=%d transactions=%d",
            len(lines),
            valid,
            skipped,
            len(items),
        )
        return items

    def _detect_header(self, table: list[list[str | None]]) -> _HeaderMap | None:
        for row in table[:4]:
            normalized = [self._normalize_cell(c) for c in row]
            date_idx = self._find_col(normalized, ("date", "txn date", "transaction date", "value date"))
            desc_idx = self._find_col(normalized, ("description", "narration", "particulars", "details"))
            debit_idx = self._find_col(normalized, ("debit", "withdrawal", "dr", "amt out", "payment"))
            credit_idx = self._find_col(normalized, ("credit", "deposit", "cr", "amt in", "receipt"))
            amount_idx = self._find_col(normalized, ("amount",))
            balance_idx = self._find_col(normalized, ("balance", "running balance", "closing balance"))
            if date_idx is not None and desc_idx is not None and (amount_idx is not None or debit_idx is not None or credit_idx is not None):
                return _HeaderMap(date_idx, desc_idx, debit_idx, credit_idx, amount_idx, balance_idx)
        return None

    def _find_col(self, headers: list[str], aliases: tuple[str, ...]) -> int | None:
        aliases_norm = [a.lower() for a in aliases]
        for idx, header in enumerate(headers):
            h = header.lower()
            if any(a in h for a in aliases_norm):
                return idx
        return None

    def _parse_table_row(self, row: list[str | None], hm: _HeaderMap) -> ParsedTransaction | None:
        raw_date = self._cell(row, hm.date_idx)
        raw_desc = self._cell(row, hm.desc_idx)
        if not raw_date or not raw_desc:
            return None
        if any(marker in raw_desc.lower() for marker in SUMMARY_MARKERS):
            return None

        tx_date = self._parse_date(raw_date)
        if tx_date is None:
            return None

        debit = self._parse_amount(self._cell(row, hm.debit_idx))
        credit = self._parse_amount(self._cell(row, hm.credit_idx))
        amount = self._parse_amount(self._cell(row, hm.amount_idx))
        balance = self._parse_amount(self._cell(row, hm.balance_idx))

        tx_type: Literal["income", "expense"] | None = None
        tx_amount: float | None = None
        if debit is not None and debit > 0:
            tx_type = "expense"
            tx_amount = float(abs(debit))
        elif credit is not None and credit > 0:
            tx_type = "income"
            tx_amount = float(abs(credit))
        elif amount is not None and amount > 0:
            if credit is not None and credit > 0:
                tx_type = "income"
            elif debit is not None and debit > 0:
                tx_type = "expense"
            else:
                tx_type = "expense"
            tx_amount = float(abs(amount))

        if tx_type is None or tx_amount is None or tx_amount <= 0:
            return None

        return ParsedTransaction(
            date=tx_date,
            description=raw_desc.strip()[:255] or "Transaction",
            amount=tx_amount,
            type=tx_type,
            balance=float(balance) if balance is not None else None,
            is_valid=True,
        )

    def _parse_ocr_lines(self, lines: list[str]) -> tuple[list[ParsedTransaction], int, int]:
        items: list[ParsedTransaction] = []
        skipped = 0
        valid = 0

        for line in lines:
            if any(marker in line.lower() for marker in SUMMARY_MARKERS):
                skipped += 1
                continue

            tx_date = self._parse_date(line)
            if tx_date is None:
                skipped += 1
                continue

            numerics = OCR_NUMERIC.findall(line.replace(",", ""))
            if len(numerics) < 2:
                skipped += 1
                continue

            balance_raw = numerics[-1]
            amount_raw = numerics[-2]
            amount_dec = self._parse_amount(amount_raw)
            balance_dec = self._parse_amount(balance_raw)
            if amount_dec is None or amount_dec <= 0:
                skipped += 1
                continue

            t = self._ocr_type(line)
            desc = line
            date_token = DATE_CANDIDATE.search(line)
            if date_token:
                desc = desc.replace(date_token.group(0), " ")
            desc = desc.replace(balance_raw, " ").replace(amount_raw, " ")
            desc = re.sub(r"\s+", " ", desc).strip(" -") or "Transaction"

            items.append(
                ParsedTransaction(
                    date=tx_date,
                    description=desc[:255],
                    amount=float(abs(amount_dec)),
                    type=t,
                    balance=float(balance_dec) if balance_dec is not None else None,
                    is_valid=True,
                )
            )
            valid += 1

        dedup: dict[tuple[str, str, int, str], ParsedTransaction] = {}
        for tx in items:
            key = (tx.date.isoformat(), tx.description.lower(), int(round(tx.amount * 100)), tx.type)
            dedup[key] = tx
        return list(dedup.values()), skipped, valid

    def _ocr_type(self, line: str) -> Literal["income", "expense"]:
        text = line.upper()
        expense_hits = any(k in text for k in ("OUTWARD", "UPI", "POS", "DEBIT", "DR", "WITHDRAW"))
        income_hits = any(k in text for k in ("INWARD", "CR", "SALARY", "CREDIT", "DEPOSIT"))
        if income_hits and not expense_hits:
            return "income"
        return "expense"

    def _clean_with_polars(self, rows: list[ParsedTransaction]) -> list[ParsedTransaction]:
        if not rows or pl is None:
            return rows
        df = pl.DataFrame(
            {
                "description": [r.description for r in rows],
            }
        )
        cleaned = (
            df.with_columns(
                pl.col("description")
                .str.replace_all(r"(?i)\bupi[-\w@./]+\b", " ")
                .str.replace_all(r"(?i)\bpos[ -]?\d+\b", " ")
                .str.replace_all(r"\b\d{6,}\b", " ")
                .str.replace_all(r"(?i)\b(?:txn|ref|utr|id|no|number)\b", " ")
                .str.replace_all(r"\s+", " ")
                .str.strip_chars()
                .alias("description")
            )
            .to_dict(as_series=False)
            .get("description", [])
        )
        normalized: list[ParsedTransaction] = []
        for idx, tx in enumerate(rows):
            desc = cleaned[idx].strip() if idx < len(cleaned) else tx.description
            normalized.append(tx.model_copy(update={"description": (desc or "Transaction")[:255]}))
        return normalized

    def verify_integrity(self, transactions: list[ParsedTransaction]) -> tuple[list[ParsedTransaction], float]:
        if not transactions:
            return transactions, 1.0

        ordered = sorted(transactions, key=lambda t: (t.date.isoformat(), t.description.lower(), t.amount, t.type))
        initial = self._infer_initial_balance(ordered)
        if initial is None:
            return ordered, 1.0

        running = initial
        validated: list[ParsedTransaction] = []
        valid_rows = 0
        for tx in ordered:
            if tx.type == "income":
                running += float(tx.amount)
            else:
                running -= float(tx.amount)

            is_valid = True
            if tx.balance is not None:
                is_valid = abs(running - float(tx.balance)) <= 1.0
            if is_valid:
                valid_rows += 1
            validated.append(tx.model_copy(update={"is_valid": is_valid}))

        score = valid_rows / len(validated) if validated else 1.0
        return validated, score

    def _infer_initial_balance(self, ordered: list[ParsedTransaction]) -> float | None:
        for tx in ordered:
            if tx.balance is None:
                continue
            if tx.type == "income":
                return float(tx.balance) - float(tx.amount)
            return float(tx.balance) + float(tx.amount)
        return None

    def _cell(self, row: list[str | None], idx: int | None) -> str:
        if idx is None or idx >= len(row):
            return ""
        return self._normalize_cell(row[idx])

    def _normalize_cell(self, value: str | None) -> str:
        return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()

    def _parse_date(self, value: str) -> date | None:
        candidate_match = DATE_CANDIDATE.search(value)
        candidate = candidate_match.group(0) if candidate_match else value.strip()
        for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(candidate, fmt).date()
            except ValueError:
                continue
        return None

    def _parse_amount(self, raw: str) -> Decimal | None:
        value = (raw or "").strip()
        if not value:
            return None
        value = value.replace("₹", "").replace("INR", "").replace("Rs.", "").replace("Rs", "").strip()
        if not value:
            return None
        match = AMOUNT_CANDIDATE.search(value)
        if not match:
            return None
        token = match.group(0).replace(",", "")
        try:
            return Decimal(token)
        except InvalidOperation:
            return None
