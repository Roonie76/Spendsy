"""
TYPE_C Parser — Scanned PDF / Unstructured document handler.

When a PDF contains little or no extractable text (e.g., it is a scanned bank
statement), this module orchestrates:

    1. OCR via pytesseract (Tesseract backend) at 220 DPI
    2. OCR character-correction (common OCR misreads for digits)
    3. Attempt structured parsing on OCR output (TYPE_A → TYPE_B → heuristic)
    4. LLM fallback when OCR confidence is too low

OCR character correction table (common misreads on bank docs):
    l → 1,  I → 1,  O → 0,  o → 0,  B → 8,  S → 5,  Z → 2,  G → 6

This correction is applied ONLY to tokens that look like pure numeric values,
not to descriptive text — otherwise we would corrupt merchant names etc.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.core.base_parser import BaseParser
from app.core.schemas import ParsedTransaction, ParserResponse

logger = logging.getLogger(__name__)

try:
    import pytesseract  # type: ignore
    _TESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None   # type: ignore[assignment]
    _TESSERACT_AVAILABLE = False

try:
    from PIL import Image  # type: ignore
    _PIL_AVAILABLE = True
except ImportError:
    Image = None          # type: ignore[assignment]
    _PIL_AVAILABLE = False

try:
    import pdfplumber  # type: ignore
    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    pdfplumber = None     # type: ignore[assignment]
    _PDFPLUMBER_AVAILABLE = False


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

@dataclass
class TypeCTransaction:
    """Normalized output of the TYPE_C (OCR) parser."""
    date: str
    description: str
    debit: float | None
    credit: float | None
    balance: float | None
    ocr_confidence: float = 0.0
    raw_line: str = field(default="", repr=False)


# ---------------------------------------------------------------------------
# OCR Character-Correction Map
# ---------------------------------------------------------------------------

# These substitutions are applied to tokens that look purely numeric
# (digits only after the substitution). This repairs common Tesseract errors
# on bank statement fonts without corrupting merchant-name text.
_OCR_CHAR_CORRECTIONS: dict[str, str] = {
    "l": "1",
    "I": "1",   # capital i → 1
    "|": "1",   # pipe → 1
    "O": "0",   # capital o → 0
    "o": "0",   # lowercase o → 0
    "B": "8",   # capital b → 8
    "S": "5",   # capital s → 5
    "Z": "2",   # capital z → 2
    "G": "6",   # capital g → 6
    "q": "9",   # q → 9
    "$": "5",   # misread dollar as 5
    ".": ".",   # decimal point — keep
    ",": ",",   # thousands sep — keep
}

# Tokens that look like a number after applying corrections (may have . and ,)
_NUMERIC_LOOKING = re.compile(r"^[\d.,OolIBSZ\|G$q\s]+$")


def _correct_ocr_token(token: str) -> str:
    """
    Apply character correction to a token that looks numeric.
    Non-numeric tokens are returned unchanged.
    """
    if not _NUMERIC_LOOKING.match(token):
        return token
    result = ""
    for ch in token:
        result += _OCR_CHAR_CORRECTIONS.get(ch, ch)
    return result


def correct_ocr_text(text: str) -> str:
    """
    Apply OCR character corrections across all numeric-looking tokens in text.

    Splits on whitespace, corrects each candidate token, then rejoins.
    Preserves original spacing structure by reconstructing token by token.
    """
    if not text:
        return text

    corrected_tokens = []
    for token in text.split():
        corrected_tokens.append(_correct_ocr_token(token))
    return " ".join(corrected_tokens)


# ---------------------------------------------------------------------------
# PDF → OCR text extraction
# ---------------------------------------------------------------------------

def extract_ocr_text(pdf_bytes: bytes, max_pages: int = 10, resolution: int = 220) -> tuple[str, float]:
    """
    Run Tesseract OCR on all pages of a scanned PDF.

    Args:
        pdf_bytes:   Raw PDF bytes.
        max_pages:   Maximum number of pages to OCR (avoids memory exhaustion).
        resolution:  DPI for rendering PDF pages to images.

    Returns:
        Tuple of (full_text, avg_confidence).
        full_text is the concatenated corrected OCR text.
        avg_confidence is the mean Tesseract word confidence (0.0–1.0).
    """
    if not _TESSERACT_AVAILABLE:
        logger.warning("type_c_parser: pytesseract not available, returning empty")
        return "", 0.0

    if not _PDFPLUMBER_AVAILABLE:
        logger.warning("type_c_parser: pdfplumber not available, returning empty")
        return "", 0.0

    pages_text: list[str] = []
    all_confidences: list[float] = []

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_idx, page in enumerate(pdf.pages[:max_pages]):
                try:
                    # Render page to PIL Image at specified DPI
                    pil_image = page.to_image(resolution=resolution).original
                    page_text, page_conf = _ocr_image(pil_image)
                    corrected = correct_ocr_text(page_text)
                    pages_text.append(corrected)
                    all_confidences.extend(page_conf)
                    logger.info(
                        "type_c_parser: page=%d chars=%d avg_conf=%.2f",
                        page_idx + 1,
                        len(corrected),
                        sum(page_conf) / len(page_conf) if page_conf else 0,
                    )
                except Exception as e:
                    logger.warning("type_c_parser: page=%d ocr_error=%s", page_idx + 1, str(e))
                    continue
    except Exception as e:
        logger.error("type_c_parser: pdf_open_error=%s", str(e))
        return "", 0.0

    full_text = "\n".join(pages_text)
    avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
    logger.info(
        "type_c_parser: ocr_complete pages=%d chars=%d avg_confidence=%.4f",
        len(pages_text), len(full_text), avg_conf,
    )
    return full_text, avg_conf


def _ocr_image(image: Any) -> tuple[str, list[float]]:
    """
    OCR a single PIL image using Tesseract.

    Returns (text, list_of_word_confidences).
    The list of confidences uses Tesseract's per-word confidence (0–100 → 0.0–1.0).
    """
    if not _TESSERACT_AVAILABLE or pytesseract is None:
        return "", []

    # Try to get word-level data for confidence scores
    try:
        data = pytesseract.image_to_data(
            image,
            config="--oem 3 --psm 6",
            output_type=pytesseract.Output.DICT,
        )
        texts = data.get("text", [])
        confs = data.get("conf", [])

        words = []
        confidences = []
        for txt, conf_val in zip(texts, confs):
            txt = (txt or "").strip()
            if not txt:
                continue
            try:
                conf_float = float(conf_val)
            except (TypeError, ValueError):
                conf_float = -1.0
            if conf_float < 0:
                continue  # Tesseract marks non-text blocks as -1
            words.append(txt)
            confidences.append(conf_float / 100.0)

        text = " ".join(words)
        return text, confidences

    except Exception:
        # Fallback: plain string extraction with no per-word confidence
        try:
            text = pytesseract.image_to_string(image, config="--oem 3 --psm 6")
            return text, []
        except Exception as e2:
            logger.warning("type_c_parser: tesseract_failed error=%s", str(e2))
            return "", []


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

class TypeCParser(BaseParser):
    """
    Parser for TYPE_C (Scanned PDF / Unstructured) bank statement text.
    Orchestrates OCR + optional LLM fallback.
    """
    @property
    def name(self) -> str:
        return "type_c"

    @property
    def version(self) -> str:
        return "1.1.0"

    @property
    def priority(self) -> int:
        return 40

    def can_handle(self, content: bytes, text: str, **kwargs: Any) -> float:
        """
        TypeC is for scanned PDFs and specialized formats.
        """
        if kwargs.get("is_scanned"):
            return 0.95
            
        fmt = kwargs.get("fmt")
        if fmt and str(fmt) == "TYPE_C":
            return 0.9
            
        # If text is extremely short, it's a good candidate for OCR
        if not text or len(text.strip()) < 50:
            return 0.8
            
        return 0.2

    def parse(self, content: bytes, text: str, **kwargs: Any) -> ParserResponse:
        """
        Parse a scanned / unstructured PDF using OCR + optional LLM fallback.
        """
        # Step 1: Run OCR if text is missing or explicitly requested
        # Note: In the pipeline, text is already extracted. For Type C, we might need to re-extract with OCR.
        # But here we assume pipepline passed us either extracted text or we use OCR on content.
        
        ocr_text = text
        ocr_conf = 0.0
        
        # If text is too sparse, run OCR on bytes
        if len(text.strip()) < 50:
            ocr_text, ocr_conf = extract_ocr_text(content)
            
        if not ocr_text.strip():
            return ParserResponse(status="ocr_empty", transactions=[], reconciliation_score=0.0)

        # Step 2: Attempt structured parsing on OCR text
        from app.core.format_detector import FormatDetector
        detector = FormatDetector()
        fmt = detector.detect(ocr_text)

        transactions: list[ParsedTransaction] = []
        method = "ocr_heuristic"
        
        # We reuse TypeAParser and TypeBParser internally
        if fmt.value == "TYPE_A":
            from app.parsers.type_a_parser import TypeAParser
            res = TypeAParser().parse(content, ocr_text)
            transactions = res.transactions
            method = "ocr_type_a"
        elif fmt.value == "TYPE_B":
            from app.parsers.type_b_parser import TypeBParser
            res = TypeBParser().parse(content, ocr_text)
            transactions = res.transactions
            method = "ocr_type_b"
        else:
            # Heuristic fallback using raw functions
            from app.parsers.type_b_parser import parse_type_b
            from app.parsers.type_a_parser import parse_type_a
            raw_txns_b = parse_type_b(ocr_text)
            raw_txns_a = parse_type_a(ocr_text)
            raw_txns = raw_txns_b if len(raw_txns_b) >= len(raw_txns_a) else raw_txns_a
            
            from datetime import datetime
            transactions = [
                ParsedTransaction(
                    date=datetime.strptime(t.date, "%Y-%m-%d").date(),
                    description=t.description,
                    debit=t.debit,
                    credit=t.credit,
                    amount=t.debit if t.debit else t.credit,
                    type="expense" if t.debit else "income",
                    balance=t.balance,
                )
                for t in raw_txns
            ]
            method = "ocr_heuristic"

        # Step 3: LLM fallback (DISABLED)
        # llm_threshold = kwargs.get("llm_confidence_threshold", 0.60)
        # if ocr_conf < llm_threshold or not transactions:
        #     from app.parsers.llm_parser import LLMParser
        #     llm_res = LLMParser().parse(content, ocr_text, filename="scanned_ocr")
        #     if llm_res.transactions and len(llm_res.transactions) >= len(transactions):
        #         transactions = llm_res.transactions
        #         method = "llm"

        return ParserResponse(
            status="success" if transactions else "no_transactions",
            reconciliation_score=0.8, # OCR is inherently less precise
            transactions=transactions,
            meta={
                "parser_name": self.name,
                "parser_version": self.version,
                "method": method,
                "ocr_confidence": round(ocr_conf, 4),
                "count": len(transactions),
            }
        )
def parse_type_c(
    pdf_bytes: bytes,
    llm_confidence_threshold: float = 0.60,
) -> tuple[list[ParsedTransaction], float, str]:
    """
    Backward compatibility wrapper for TypeCParser.
    """
    parser = TypeCParser()
    res = parser.parse(pdf_bytes, "", llm_confidence_threshold=llm_confidence_threshold)
    method = res.meta.get("method", "ocr_heuristic")
    ocr_conf = res.meta.get("ocr_confidence", 0.0)
    return res.transactions, ocr_conf, method
