"""
FileTypeDetector — identifies file type from magic bytes and extension.
Returns: PDF | EXCEL | CSV | IMAGE | TEXT
"""
from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Magic byte signatures
_PDF_MAGIC    = b"%PDF"
_ZIP_MAGIC    = b"PK\x03\x04"
_XLS_MAGIC    = b"\xd0\xcf\x11\xe0"


class FileType(str, Enum):
    PDF   = "PDF"
    EXCEL = "EXCEL"
    CSV   = "CSV"
    IMAGE = "IMAGE"
    TEXT  = "TEXT"


class FileTypeDetector:
    @staticmethod
    def detect(file_path: str) -> FileType:
        path = Path(file_path)
        ext  = path.suffix.lower()

        # Read magic bytes
        try:
            with open(file_path, "rb") as fh:
                magic = fh.read(8)
        except OSError as e:
            logger.error("FileTypeDetector: cannot read file %s: %s", file_path, e)
            raise

        # PDF
        if magic[:4] == _PDF_MAGIC:
            return FileType.PDF

        # XLSX (zip archive with Office content)
        if magic[:4] == _ZIP_MAGIC:
            try:
                import zipfile
                with zipfile.ZipFile(file_path) as z:
                    if "[Content_Types].xml" in z.namelist():
                        return FileType.EXCEL
            except Exception:
                pass

        # Legacy XLS (OLE2 Compound Document)
        if magic[:4] == _XLS_MAGIC:
            return FileType.EXCEL

        # Extension-based fallbacks
        if ext == ".csv":
            return FileType.CSV
        if ext in (".xlsx", ".xls"):
            return FileType.EXCEL
        if ext in (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"):
            return FileType.IMAGE
        if ext in (".txt", ".text"):
            return FileType.TEXT

        # Sniff CSV: if file has mostly printable text and commas / tabs
        try:
            text_sample = magic.decode("utf-8", errors="replace")
            if "," in text_sample or "\t" in text_sample:
                return FileType.CSV
        except Exception:
            pass

        return FileType.TEXT
