from __future__ import annotations
import io
import logging
import csv
from abc import ABC, abstractmethod
from typing import Any

import pdfplumber
try:
    import openpyxl
except ImportError:
    openpyxl = None

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, content: bytes) -> str:
        pass

class PDFExtractor(BaseExtractor):
    def extract(self, content: bytes) -> str:
        text_parts = []
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        text_parts.append(text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {str(e)}")
            return ""

class CSVExtractor(BaseExtractor):
    def extract(self, content: bytes) -> str:
        try:
            text = content.decode("utf-8-sig", errors="replace")
            # We return the first 100 rows as text for quality detection
            # but usually CSV is highly structured, so we just return a sample
            lines = text.splitlines()
            return "\n".join(lines[:200])
        except Exception as e:
            logger.error(f"Failed to extract CSV text: {str(e)}")
            return ""

class XLSXExtractor(BaseExtractor):
    def extract(self, content: bytes) -> str:
        if not openpyxl:
            logger.warning("openpyxl not installed, cannot extract XLSX")
            return ""
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            text_parts = []
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True, max_row=100):
                    row_text = " ".join([str(cell) for cell in row if cell is not None])
                    if row_text:
                        text_parts.append(row_text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Failed to extract XLSX text: {str(e)}")
            return ""

class TextExtractor(BaseExtractor):
    def extract(self, content: bytes) -> str:
        try:
            return content.decode("utf-8", errors="replace").strip()
        except Exception as e:
            logger.error(f"Failed to extract text: {str(e)}")
            return ""

def get_extractor(content_type: str, filename: str) -> BaseExtractor:
    filename = filename.lower()
    if filename.endswith(".pdf") or "pdf" in content_type:
        return PDFExtractor()
    if filename.endswith(".csv") or "csv" in content_type:
        return CSVExtractor()
    if filename.endswith((".xlsx", ".xls")) or "spreadsheet" in content_type or "excel" in content_type:
        return XLSXExtractor()
    if filename.endswith(".txt") or "text/plain" in content_type:
        return TextExtractor()
    return TextExtractor() # Safer default fallback for unknown text formats
