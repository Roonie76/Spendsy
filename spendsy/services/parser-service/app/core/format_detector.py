"""
Format Detection Module — TYPE_A / TYPE_B / TYPE_C classifier.

Classification rules (deterministic, no ML required):
    TYPE_A  — Structured tables: keywords 'withdrawal', 'deposit', 'balance'
              Typical banks: HDFC, ICICI, Axis, Kotak, Yes Bank
    TYPE_B  — DR/CR indicator format: keywords 'dr', 'cr' as column headers
              Typical banks: SBI, PNB, BOB, Canara, other PSU banks
    TYPE_C  — Scanned / unstructured: little or no extractable text
              Requires OCR to recover data

Decision tree:
    extracted_text is empty?             → TYPE_C (scanned)
    keyword 'dr' or 'cr' on its own?     → TYPE_B
    keyword 'withdrawal' or 'deposit'?   → TYPE_A
    tabular_density >= threshold?        → TYPE_A (implicit structured)
    else                                 → TYPE_C (treat as unstructured / scanned)
"""

from __future__ import annotations

import logging
import re
from enum import Enum

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BankStatementFormat(str, Enum):
    TYPE_A = "TYPE_A"   # Structured table (HDFC / ICICI / Axis)
    TYPE_B = "TYPE_B"   # DR/CR indicator (SBI / PNB / PSU banks)
    TYPE_C = "TYPE_C"   # Scanned / unstructured PDF

class PageClassification(str, Enum):
    DIGITAL = "DIGITAL"
    SCANNED = "SCANNED"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Compiled patterns for detection
# ---------------------------------------------------------------------------

# TYPE_A signals — explicit column headers or clear labels
_TYPE_A_PAT = re.compile(
    r"\b(withdrawal|deposit|deposits|withdrawals|narration|particulars|chq|ref|balance|amount|credit|debit)\b",
    re.IGNORECASE,
)

# TYPE_B signals — DR/CR as standalone column labels (not inline text like "DR AMOUNT")
# Matches when 'DR' or 'CR' appears as its own column header token, possibly surrounded by whitespace
_TYPE_B_COL_PAT = re.compile(
    r"(?:^|\s)(?:dr|cr)(?:\s|$)",
    re.IGNORECASE | re.MULTILINE,
)

# DR/CR inline within transaction rows (stronger signal for TYPE_B)
_TYPE_B_INLINE_PAT = re.compile(
    r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b.{1,80}\b(DR|CR)\b",
    re.IGNORECASE,
)

# Date + Amount heuristic for tabular density check
_DATE_PAT = re.compile(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b")
_AMOUNT_PAT = re.compile(r"\d+[,.]\d{2}\b")


# ---------------------------------------------------------------------------
# Main detector class
# ---------------------------------------------------------------------------

class FormatDetector:
    """
    Classifies a bank statement's extracted text into one of three formats:
        TYPE_A, TYPE_B, or TYPE_C

    Usage:
        detector = FormatDetector()
        fmt = detector.detect(text)
    """

    # Minimum ratio of lines containing both a date and amount to be TYPE_A
    _TYPE_A_TABULAR_THRESHOLD = 0.15

    # Minimum number of TYPE_B inline matches to classify as TYPE_B
    _TYPE_B_INLINE_MIN = 2

    def detect(self, text: str) -> BankStatementFormat:
        """
        Classify text into TYPE_A, TYPE_B, or TYPE_C.

        Args:
            text: Raw text extracted from the PDF (may be empty for scanned docs).

        Returns:
            BankStatementFormat enum value.
        """
        if not text or not text.strip():
            # No extractable text → almost certainly a scanned PDF
            logger.info("format_detect=TYPE_C reason=empty_text")
            return BankStatementFormat.TYPE_C

        lines = text.splitlines()
        line_count = len(lines)

        if line_count == 0:
            return BankStatementFormat.TYPE_C

        # ---- Step 1: Check for TYPE_B signals (before TYPE_A, since SBI often
        #              also has words like 'balance' which would hit TYPE_A).

        type_b_inline_count = len(_TYPE_B_INLINE_PAT.findall(text))
        type_b_col_matches = len(_TYPE_B_COL_PAT.findall(text))

        if type_b_inline_count >= self._TYPE_B_INLINE_MIN or type_b_col_matches >= 3:
            logger.info(
                "format_detect=TYPE_B reason=dr_cr_signals inline=%d col=%d",
                type_b_inline_count,
                type_b_col_matches,
            )
            return BankStatementFormat.TYPE_B

        # ---- Step 2: Check for TYPE_A keyword signals in header/top section

        # Scan only the first 50 lines for header keywords (avoids matching
        # keywords that appear incidentally in narrations later)
        header_text = "\n".join(lines[:50])
        type_a_keyword_hit = bool(_TYPE_A_PAT.search(header_text))

        if type_a_keyword_hit:
            logger.info("format_detect=TYPE_A reason=keyword_header")
            return BankStatementFormat.TYPE_A

        # ---- Step 3: Tabular density fallback for TYPE_A

        tabular_lines = sum(
            1
            for line in lines
            if _DATE_PAT.search(line) and _AMOUNT_PAT.search(line)
        )
        tabular_density = tabular_lines / line_count

        if line_count >= 3 and tabular_density >= self._TYPE_A_TABULAR_THRESHOLD:
            logger.info(
                "format_detect=TYPE_A reason=tabular_density density=%.3f",
                tabular_density,
            )
            return BankStatementFormat.TYPE_A

        # ---- Step 4: Fall back to TYPE_C (probably garbled / scanned)

        logger.info(
            "format_detect=TYPE_C reason=low_density density=%.3f",
            tabular_density,
        )
        return BankStatementFormat.TYPE_C

    def probe_file_type(self, text: str) -> PageClassification:
        """Determines if the file is digital or scanned at a document level."""
        if not text or not text.strip():
            return PageClassification.SCANNED
        
        lines = text.splitlines()
        page_checks = []
        
        # Heuristic: split text into 'pages' by formfeed or large gaps (naive)
        pages = text.split('\f')
        for p in pages:
            if len(p.strip()) < 100:
                page_checks.append(PageClassification.SCANNED)
            elif "(cid:" in p:
                page_checks.append(PageClassification.SCANNED) # Likely garbled
            else:
                # Check for printable ratio
                printable = sum(1 for c in p if c.isalnum() or c.isspace() or c in ".,/-():;")
                if (printable / len(p)) < 0.6:
                    page_checks.append(PageClassification.SCANNED)
                else:
                    page_checks.append(PageClassification.DIGITAL)
        
        scanned_count = page_checks.count(PageClassification.SCANNED)
        digital_count = page_checks.count(PageClassification.DIGITAL)
        
        if scanned_count > 0 and digital_count > 0:
            return PageClassification.MIXED
        if scanned_count > 0:
            return PageClassification.SCANNED
        return PageClassification.DIGITAL

    def detect_bank(self, text: str) -> str:
        """Identify the bank name from the statement text using keyword fingerprinting."""
        t = text.upper()
        
        # Bank Fingerprints
        fingerprints = {
            "HDFC": ["HDFC BANK", "HDFC STATEMENT", "HDFC LTD"],
            "SBI": ["STATE BANK OF INDIA", "SBI STATEMENT", "ONLINESBI"],
            "ICICI": ["ICICI BANK", "ICICI STATEMENT"],
            "Axis": ["AXIS BANK", "AXIS STATEMENT"],
            "Kotak": ["KOTAK MAHINDRA", "KOTAK BANK"],
            "Yes Bank": ["YES BANK", "YESBANK"],
            "IDFC": ["IDFC FIRST", "IDFC BANK"],
            "IndusInd": ["INDUSIND BANK"],
            "Citibank": ["CITIBANK", "CITI BANK"],
            "Standard Chartered": ["STANDARD CHARTERED", "SC BANK"],
            "HSBC": ["HSBC BANK", "HSBC STATEMENT"],
        }
        
        for bank, keywords in fingerprints.items():
            if any(kw in t for kw in keywords):
                return bank
                
        return "Unknown"

    def is_scanned_pdf(self, text: str) -> bool:
        """Return True if the PDF appears to be a scanned image (no real text)."""
        if not text or not text.strip():
            return True
        # Very short text relative to a real document also suggests scan
        words = text.split()
        return len(words) < 10


# Module-level singleton
format_detector = FormatDetector()
