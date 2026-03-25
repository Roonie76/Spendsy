"""
BankStatementOrchestrator — top-level entry point that ties together:
  FileTypeDetector → PDFTypeProbe → (Digital|OCR)Pipeline
  → BankIdentifier → BankParserRegistry → BalanceReconciler
  → Post-processing (deduplicate, sort)
  → StatementResult

Usage:
    from app.core.bank_orchestrator import BankStatementOrchestrator
    result = BankStatementOrchestrator().parse(content, filename="Jan.pdf")
"""
from __future__ import annotations

import logging
import tempfile
import os
import time
from dataclasses import dataclass, field
from decimal import Decimal

from app.classifier.file_type_detector import FileTypeDetector, FileType
from app.classifier.bank_identifier import BankIdentifier
from app.core.pdf_type_probe import PDFTypeProbe, PDFType
from app.pipelines.digital_pipeline import DigitalPDFPipeline
from app.pipelines.ocr_pipeline import OCRPipeline
from app.parsers.banks.base import AccountInfo, BankTransaction, StatementSummary
from app.parsers.banks.hdfc import HDFCParser
from app.parsers.banks.sbi import SBIParser
from app.parsers.banks.icici import ICICIParser
from app.parsers.banks.axis_kotak import AxisParser, KotakParser
from app.parsers.banks.generic import GenericParser
from app.extractors.balance_reconciler import BalanceReconciler, ReconciliationReport
from app.postprocessing.deduplicator import Deduplicator

logger = logging.getLogger(__name__)


@dataclass
class StatementResult:
    account_info:   AccountInfo
    transactions:   list[BankTransaction]
    summary:        StatementSummary
    reconciliation: ReconciliationReport
    bank_id:        str
    pdf_type:       str
    transaction_count: int = 0
    parse_time_ms:  int = 0
    errors:         list[str] = field(default_factory=list)


# ── Bank parser registry (ordered by priority) ──────────────────────────────
_ALL_PARSERS = [
    HDFCParser(),
    SBIParser(),
    ICICIParser(),
    AxisParser(),
    KotakParser(),
    GenericParser(),
]

_PARSER_MAP = {p.bank_id: p for p in _ALL_PARSERS}


def _get_parser(bank_id: str):
    return _PARSER_MAP.get(bank_id, GenericParser())


def _excel_pipeline_pages(content: bytes, filename: str) -> list:
    """Convert Excel/CSV content to the same PageData format used by PDF pipelines."""
    try:
        import csv, io as _io, openpyxl
        from app.pipelines.digital_pipeline import PageData
        ext = (filename or "").lower()
        if ext.endswith(".csv"):
            try:
                import chardet
                enc = chardet.detect(content)["encoding"] or "utf-8"
            except ImportError:
                enc = "utf-8"
            text = content.decode(enc, errors="replace")
            reader = csv.reader(_io.StringIO(text))
            rows = [[str(c) for c in row] for row in reader if any(row)]
            raw = text
        else:
            wb = openpyxl.load_workbook(_io.BytesIO(content), read_only=True, data_only=True)
            rows = []
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    clean = [str(c) if c is not None else "" for c in row]
                    if any(clean):
                        rows.append(clean)
            raw = "\n".join(" | ".join(r) for r in rows)
        page = PageData(page_number=0, tables=[rows], raw_text=raw, method_used="excel_csv")
        return [page]
    except Exception as e:
        logger.error("_excel_pipeline_pages: %s", e)
        return []


class BankStatementOrchestrator:

    def parse(self, content: bytes, filename: str = "statement.pdf") -> StatementResult:
        t0 = time.time()

        # ── 1. Detect file type ──────────────────────────────────────────
        try:
            with tempfile.NamedTemporaryFile(suffix=os.path.splitext(filename)[1], delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            file_type = FileTypeDetector.detect(tmp_path)
        except Exception as e:
            logger.error("FileTypeDetector failed: %s", e)
            file_type = FileType.PDF
            tmp_path  = None

        # ── 2. Extract raw page data ─────────────────────────────────────
        pdf_type = "N/A"
        all_pages: list = []

        if file_type == FileType.PDF:
            probe    = PDFTypeProbe.classify_bytes(content)
            pdf_type = probe.value
            logger.info("BankOrchestrator: file=%s pdf_type=%s", filename, pdf_type)

            if probe == PDFType.SCANNED:
                all_pages = OCRPipeline().run_bytes(content)
            elif probe == PDFType.MIXED:
                # Run digital first; OCR for pages with no tables
                digital_pages = DigitalPDFPipeline().run_bytes(content)
                ocr_pages     = OCRPipeline().run_bytes(content)
                all_pages = []
                for d, o in zip(digital_pages, ocr_pages):
                    all_pages.append(d if d.tables else o)
            else:
                all_pages = DigitalPDFPipeline().run_bytes(content)

        elif file_type in (FileType.EXCEL, FileType.CSV):
            all_pages = _excel_pipeline_pages(content, filename)
            pdf_type  = "EXCEL_CSV"
        else:
            all_pages = DigitalPDFPipeline().run_bytes(content)

        # Cleanup temp file
        if tmp_path:
            try: os.unlink(tmp_path)
            except Exception: pass

        if not all_pages:
            logger.warning("BankOrchestrator: no pages extracted from %s", filename)
            return StatementResult(
                account_info=AccountInfo(), transactions=[],
                summary=StatementSummary(), reconciliation=ReconciliationReport(),
                bank_id="GENERIC", pdf_type=pdf_type,
                errors=["No pages extracted"],
            )

        # ── 3. Identify bank ─────────────────────────────────────────────
        probe_text = "\n".join(getattr(p, "raw_text", "") for p in all_pages[:2])
        bank_id    = BankIdentifier.identify(probe_text)
        parser     = _get_parser(bank_id)
        logger.info("BankOrchestrator: bank_id=%s parser=%s", bank_id, parser.__class__.__name__)

        # ── 4. Extract fields ────────────────────────────────────────────
        account_info = parser.extract_header(all_pages)
        transactions = parser.extract_table(all_pages)
        summary      = parser.extract_summary(all_pages)

        # ── 5. Dedup + sort ──────────────────────────────────────────────
        transactions = Deduplicator.deduplicate(transactions)
        transactions.sort(key=lambda t: t.date)

        # ── 6. Balance reconciliation ────────────────────────────────────
        recon = BalanceReconciler.reconcile(transactions, summary.opening_balance)

        elapsed_ms = int((time.time() - t0) * 1000)
        logger.info("BankOrchestrator: bank=%s txns=%d drift_rows=%d time=%dms",
                    bank_id, len(transactions), len(recon.drift_rows), elapsed_ms)

        return StatementResult(
            account_info      = account_info,
            transactions      = transactions,
            summary           = summary,
            reconciliation    = recon,
            bank_id           = bank_id,
            pdf_type          = pdf_type,
            transaction_count = len(transactions),
            parse_time_ms     = elapsed_ms,
        )
