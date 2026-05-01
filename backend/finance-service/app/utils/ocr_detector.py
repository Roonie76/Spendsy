from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pdfplumber


SIGNAL_WEIGHTS = {
    "text_density": 0.35,
    "font_presence": 0.20,
    "image_coverage": 0.20,
    "producer_meta": 0.15,
    "word_selectability": 0.10,
}

OCR_THRESHOLD = float(os.getenv("SPENDSY_OCR_THRESHOLD", "0.55"))
HIGH_TEXT_VOLUME_CHARS = 5_000

OCR_KEYWORDS = (
    "tesseract",
    "abbyy",
    "adobe acrobat ocr",
    "nuance",
    "readiris",
    "omnipage",
)

UTILITY_KEYWORDS = (
    "ilovepdf",
    "smallpdf",
    "pdf24",
    "sejda",
    "pdfescape",
    "ghostscript",
    "microsoft",
    "libreoffice",
    "reportlab",
    "fpdf",
    "wkhtmltopdf",
)


class OcrRequiredError(ValueError):
    """Raised when the statement parser should route a PDF to OCR."""

    def __init__(self, debug_info: dict[str, Any]):
        super().__init__("OCR_REQUIRED: PDF appears to be scanned. Use an OCR pipeline.")
        self.debug_info = debug_info


def _score_text_density(avg_chars_per_page: float) -> float:
    if avg_chars_per_page > 500:
        return 0.0
    if avg_chars_per_page > 200:
        return 0.2
    if avg_chars_per_page > 50:
        return 0.7
    return 1.0


def _score_font_presence(font_count: int) -> float:
    if font_count >= 3:
        return 0.0
    if font_count == 2:
        return 0.2
    if font_count == 1:
        return 0.6
    return 1.0


def _score_image_coverage(avg_image_ratio: float) -> float:
    if avg_image_ratio < 0.15:
        return 0.0
    if avg_image_ratio < 0.40:
        return 0.3
    if avg_image_ratio < 0.70:
        return 0.7
    return 1.0


def _score_producer_meta(metadata: dict[str, Any] | None) -> float:
    metadata = metadata or {}
    producer = str(metadata.get("Producer") or metadata.get("producer") or "").lower()
    creator = str(metadata.get("Creator") or metadata.get("creator") or "").lower()
    combined_meta = f"{producer} {creator}"

    if any(keyword in combined_meta for keyword in OCR_KEYWORDS):
        return 1.0
    if any(keyword in combined_meta for keyword in UTILITY_KEYWORDS):
        return 0.0
    return 0.5


def _score_word_selectability(words_per_page: float) -> float:
    if words_per_page > 80:
        return 0.0
    if words_per_page > 30:
        return 0.3
    if words_per_page > 5:
        return 0.7
    return 1.0


def _image_area_ratio(page: Any) -> float:
    page_area = float(page.width or 0) * float(page.height or 0)
    if page_area <= 0:
        return 0.0

    image_area = 0.0
    for image in getattr(page, "images", []) or []:
        width = image.get("width")
        height = image.get("height")
        if width is None or height is None:
            x0 = float(image.get("x0") or 0)
            x1 = float(image.get("x1") or 0)
            top = float(image.get("top") or 0)
            bottom = float(image.get("bottom") or 0)
            width = max(0.0, x1 - x0)
            height = max(0.0, bottom - top)
        image_area += float(width or 0) * float(height or 0)

    return min(image_area / page_area, 1.0)


def analyze_pdf_signals_from_pdf(pdf: Any) -> dict[str, Any]:
    """
    Return OCR evidence for an open pdfplumber PDF.

    Each signal is in [0.0, 1.0], where 1.0 is strong OCR/image evidence and
    0.0 is strong native-digital evidence.
    """
    pages = list(getattr(pdf, "pages", []) or [])
    page_count = max(len(pages), 1)

    total_chars = 0
    total_words = 0
    font_names: set[str] = set()
    image_ratios: list[float] = []

    for page in pages:
        text = page.extract_text() or ""
        total_chars += len(text)
        total_words += len(page.extract_words() or [])
        image_ratios.append(_image_area_ratio(page))

        for char in getattr(page, "chars", []) or []:
            font_name = char.get("fontname")
            if font_name:
                font_names.add(str(font_name))

    avg_chars_per_page = total_chars / page_count
    words_per_page = total_words / page_count
    avg_image_ratio = sum(image_ratios) / max(len(image_ratios), 1)

    signals = {
        "text_density": _score_text_density(avg_chars_per_page),
        "font_presence": _score_font_presence(len(font_names)),
        "image_coverage": _score_image_coverage(avg_image_ratio),
        "producer_meta": _score_producer_meta(getattr(pdf, "metadata", None)),
        "word_selectability": _score_word_selectability(words_per_page),
    }

    return {
        "signals": signals,
        "metrics": {
            "total_chars": total_chars,
            "page_count": len(pages),
            "avg_chars_per_page": round(avg_chars_per_page, 2),
            "font_count": len(font_names),
            "avg_image_coverage": round(avg_image_ratio, 4),
            "words_per_page": round(words_per_page, 2),
        },
    }


def classify_pdf_from_pdf(pdf: Any) -> tuple[bool, dict[str, Any]]:
    analysis = analyze_pdf_signals_from_pdf(pdf)
    total_chars = analysis["metrics"]["total_chars"]
    if total_chars > HIGH_TEXT_VOLUME_CHARS:
        return False, {
            "fast_exit": "high_text_volume",
            "total_chars": total_chars,
            "threshold": OCR_THRESHOLD,
            "verdict": "native",
        }

    signals = analysis["signals"]
    score = sum(SIGNAL_WEIGHTS[key] * signals[key] for key in SIGNAL_WEIGHTS)
    is_ocr = score >= OCR_THRESHOLD
    return is_ocr, {
        **analysis,
        "weighted_score": round(score, 4),
        "threshold": OCR_THRESHOLD,
        "verdict": "ocr" if is_ocr else "native",
    }


def analyze_pdf_signals(path: str | Path) -> dict[str, Any]:
    with pdfplumber.open(str(path)) as pdf:
        return analyze_pdf_signals_from_pdf(pdf)


def is_ocr_pdf(path: str | Path) -> tuple[bool, dict[str, Any]]:
    with pdfplumber.open(str(path)) as pdf:
        return classify_pdf_from_pdf(pdf)
