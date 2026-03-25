"""
DigitalPDFPipeline — extracts tabular data from native (non-scanned) PDFs.

Extraction strategy per page (waterfall):
  1. pdfplumber table extraction   → for bordered/standard tables
  2. camelot lattice mode          → for HDFC-style ruled-line tables
  3. camelot stream mode           → for SBI-style whitespace columns
  4. pdfplumber text + word coords → for ICICI/generic mixed layouts
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Any

import pdfplumber

logger = logging.getLogger(__name__)

try:
    import camelot
    _CAMELOT_AVAILABLE = True
except ImportError:
    camelot = None  # type: ignore
    _CAMELOT_AVAILABLE = False


Y_TOLERANCE = 4  # px — words within this Y-range are on the same row


@dataclass
class PageData:
    page_number: int
    tables: list[list[list[str]]] = field(default_factory=list)
    raw_text: str = ""
    words_with_coords: list[dict] = field(default_factory=list)
    method_used: str = "unknown"


class DigitalPDFPipeline:
    """Runs the waterfall extraction strategy on a digital PDF file path."""

    def run(self, file_path: str) -> list[PageData]:
        all_pages: list[PageData] = []
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    page_data = self._process_page(page, file_path, page_idx)
                    all_pages.append(page_data)
        except Exception as e:
            logger.error("DigitalPDFPipeline.run: error=%s", e)
        return all_pages

    def run_bytes(self, content: bytes) -> list[PageData]:
        """Same as run() but accepts raw PDF bytes instead of a file path."""
        all_pages: list[PageData] = []
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    # camelot needs a file on disk; skip camelot fallback for bytes mode
                    page_data = self._try_pdfplumber(page, page_idx)
                    if not page_data.tables:
                        words = page.extract_words() or []
                        page_data.tables = [TextLayoutParser.parse(words)]
                        page_data.method_used = "text_layout"
                    page_data.raw_text = page.extract_text() or ""
                    page_data.words_with_coords = [
                        {"text": w["text"], "x0": w["x0"], "top": w["top"],
                         "x1": w["x1"], "bottom": w["bottom"]}
                        for w in (page.extract_words() or [])
                    ]
                    all_pages.append(page_data)
        except Exception as e:
            logger.error("DigitalPDFPipeline.run_bytes: error=%s", e)
        return all_pages

    def _process_page(self, page: Any, file_path: str, page_idx: int) -> PageData:
        pd = self._try_pdfplumber(page, page_idx)

        if not pd.tables and _CAMELOT_AVAILABLE:
            pd = self._try_camelot(file_path, page_idx, "lattice", pd)

        if not pd.tables and _CAMELOT_AVAILABLE:
            pd = self._try_camelot(file_path, page_idx, "stream", pd)

        if not pd.tables:
            words = page.extract_words() or []
            pd.tables = [TextLayoutParser.parse(words)]
            pd.method_used = "text_layout"

        pd.raw_text = page.extract_text() or ""
        pd.words_with_coords = [
            {"text": w["text"], "x0": w["x0"], "top": w["top"],
             "x1": w["x1"], "bottom": w["bottom"]}
            for w in (page.extract_words() or [])
        ]
        return pd

    @staticmethod
    def _try_pdfplumber(page: Any, page_idx: int) -> PageData:
        pd = PageData(page_number=page_idx)
        try:
            tables = page.extract_tables() or []
            cleaned = []
            for table in tables:
                clean_table = []
                for row in table:
                    clean_row = [str(cell or "").strip() for cell in row]
                    if any(c for c in clean_row):
                        clean_table.append(clean_row)
                if clean_table:
                    cleaned.append(clean_table)
            if cleaned:
                pd.tables = cleaned
                pd.method_used = "pdfplumber_table"
        except Exception as e:
            logger.debug("pdfplumber table extraction failed page=%d: %s", page_idx, e)
        return pd

    @staticmethod
    def _try_camelot(file_path: str, page_idx: int, flavor: str, pd: PageData) -> PageData:
        min_accuracy = 80 if flavor == "lattice" else 70
        try:
            tables = camelot.read_pdf(
                file_path,
                pages=str(page_idx + 1),
                flavor=flavor,
                suppress_stdout=True,
            )
            good_tables = [t for t in tables if t.parsing_report.get("accuracy", 0) >= min_accuracy]
            if good_tables:
                pd.tables = [
                    [[str(cell) for cell in row] for row in t.df.values.tolist()]
                    for t in good_tables
                ]
                pd.method_used = f"camelot_{flavor}"
        except Exception as e:
            logger.debug("camelot %s failed page=%d: %s", flavor, page_idx, e)
        return pd


class TextLayoutParser:
    """Reconstructs a table from pdfplumber word-coordinate dicts."""

    @staticmethod
    def parse(words: list[dict]) -> list[list[str]]:
        if not words:
            return []

        # Cluster words into rows by Y-coordinate proximity
        rows: dict[float, list[dict]] = {}
        for w in words:
            y_center = (w.get("top", 0) + w.get("bottom", 0)) / 2
            matched = None
            for existing_y in rows:
                if abs(existing_y - y_center) <= Y_TOLERANCE:
                    matched = existing_y
                    break
            if matched is None:
                rows[y_center] = [w]
            else:
                rows[matched].append(w)

        result = []
        for y_key in sorted(rows):
            sorted_words = sorted(rows[y_key], key=lambda w: w.get("x0", 0))
            result.append([w["text"] for w in sorted_words])
        return result
