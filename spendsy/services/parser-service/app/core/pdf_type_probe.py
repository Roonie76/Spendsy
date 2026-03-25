"""
PDFTypeProbe — classifies each page of a PDF as DIGITAL or SCANNED.
Returns overall document type: DIGITAL | SCANNED | MIXED
"""
from __future__ import annotations

import io
import logging
from enum import Enum

import pdfplumber

logger = logging.getLogger(__name__)


class PDFType(str, Enum):
    DIGITAL = "DIGITAL"
    SCANNED = "SCANNED"
    MIXED   = "MIXED"


class PDFTypeProbe:
    @staticmethod
    def classify_bytes(content: bytes) -> PDFType:
        digital = 0
        scanned = 0
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    text        = page.extract_text() or ""
                    char_count  = len(text.strip())
                    image_count = len(page.images)

                    if char_count > 50 and image_count == 0:
                        digital += 1
                    elif char_count < 20 and image_count >= 1:
                        scanned += 1
                    elif char_count > 50 and image_count >= 1:
                        # Text + image — check if text positions are reasonable
                        words = page.extract_words() or []
                        if len(words) > 10:
                            digital += 1
                        else:
                            scanned += 1
                    else:
                        scanned += 1
        except Exception as e:
            logger.warning("PDFTypeProbe: error=%s — defaulting to DIGITAL", e)
            return PDFType.DIGITAL

        total = digital + scanned
        if total == 0:
            return PDFType.DIGITAL

        ratio = digital / total
        if ratio >= 0.85:
            return PDFType.DIGITAL
        elif ratio <= 0.15:
            return PDFType.SCANNED
        else:
            return PDFType.MIXED
