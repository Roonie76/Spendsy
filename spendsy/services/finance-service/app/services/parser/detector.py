import pdfplumber
from pypdf import PdfReader
from pdf2image import convert_from_bytes
import pytesseract
import logging
import io

logger = logging.getLogger("finance.parser.detector")

def detect_pdf_type(content: bytes) -> str:
    """
    Classifies every incoming PDF into one of three types by sampling the first 3 pages.
    Returns: 'ocr_scanned' | 'structured_ledger' | 'unstructured_text'
    """
    # Use BytesIO for pypdf and pdfplumber
    pdf_file = io.BytesIO(content)
    
    try:
        reader = PdfReader(pdf_file)
        total_pages = len(reader.pages)
    except Exception as e:
        logger.error(f"Failed to read PDF with pypdf: {e}")
        return "unstructured_text" # Fallback

    # Sample first 3 pages for efficiency
    sample_pages = min(3, total_pages)
    extracted_text = ""
    table_count = 0

    try:
        pdf_file.seek(0)
        with pdfplumber.open(pdf_file) as pdf:
            for i in range(sample_pages):
                page = pdf.pages[i]
                text = page.extract_text() or ""
                extracted_text += text
                tables = page.extract_tables()
                table_count += len(tables)
    except Exception as e:
        logger.error(f"Failed to extract text/tables with pdfplumber: {e}")
        # If pdfplumber fails, we might still have a scanned PDF or just a corrupt one
        return "ocr_scanned" if total_pages > 0 else "unstructured_text"

    char_count = len(extracted_text.strip())
    logger.info(f"PDF Detection: char_count={char_count}, table_count={table_count}, pages={total_pages}")

    # Rule 1: No extractable text → scanned/OCR PDF
    if char_count < 50:
        logger.info("Classified as ocr_scanned")
        return "ocr_scanned"

    # Rule 2: Rich table structure → structured ledger
    avg_tables_per_page = table_count / sample_pages
    has_numeric_density = sum(c.isdigit() for c in extracted_text) / max(char_count, 1) > 0.15

    if avg_tables_per_page >= 1 or has_numeric_density:
        logger.info(f"Classified as structured_ledger (avg_tables={avg_tables_per_page:.2f}, numeric_density={has_numeric_density:.2f})")
        return "structured_ledger"

    # Rule 3: Text-rich but unstructured
    logger.info("Classified as unstructured_text")
    return "unstructured_text"
