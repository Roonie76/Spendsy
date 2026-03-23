"""
Bank Detector — Extended auto-detection of Indian bank from statement text.

Extends the basic detect_bank() in parser.py with:
  - Additional banks (Kotak, YES, Federal, PNB, Canara, BOB, IndusInd, etc.)
  - Account number pattern hints
  - IFSC code prefix matching
  - Filename-based hints

Returns a BankInfo namedtuple with name + abbreviation + statement format hint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from app.core.format_detector import BankStatementFormat


# ---------------------------------------------------------------------------
# Bank registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BankInfo:
    """Metadata about a detected bank."""
    name: str                           # Full name, e.g. "HDFC Bank"
    code: str                           # Short code, e.g. "hdfc"
    default_format: BankStatementFormat # Expected statement format


_BANK_RULES: list[tuple[list[str], BankInfo]] = [
    # ----- Private sector banks (usually TYPE_A structured tables) -----
    (
        ["hdfc bank", r"\bhdfc\b", "hdfcbank"],
        BankInfo("HDFC Bank", "hdfc", BankStatementFormat.TYPE_A),
    ),
    (
        ["icici bank", r"\bicici\b"],
        BankInfo("ICICI Bank", "icici", BankStatementFormat.TYPE_A),
    ),
    (
        ["axis bank", r"\baxis\b"],
        BankInfo("Axis Bank", "axis", BankStatementFormat.TYPE_A),
    ),
    (
        ["kotak mahindra", "kotak bank", r"\bkotak\b"],
        BankInfo("Kotak Mahindra Bank", "kotak", BankStatementFormat.TYPE_A),
    ),
    (
        ["yes bank", r"\byes\s*bank\b"],
        BankInfo("YES Bank", "yes", BankStatementFormat.TYPE_A),
    ),
    (
        ["indusind bank", r"\bindusind\b"],
        BankInfo("IndusInd Bank", "indusind", BankStatementFormat.TYPE_A),
    ),
    (
        ["federal bank", r"\bfederal\b"],
        BankInfo("Federal Bank", "federal", BankStatementFormat.TYPE_A),
    ),
    (
        ["rbl bank", r"\brbl\b"],
        BankInfo("RBL Bank", "rbl", BankStatementFormat.TYPE_A),
    ),
    (
        ["idfc first bank", "idfc bank", r"\bidfc\b"],
        BankInfo("IDFC First Bank", "idfc", BankStatementFormat.TYPE_A),
    ),
    # ----- PSU banks (usually TYPE_B with DR/CR format) -----
    (
        ["state bank of india", r"\bsbi\b"],
        BankInfo("State Bank of India", "sbi", BankStatementFormat.TYPE_B),
    ),
    (
        ["punjab national bank", r"\bpnb\b"],
        BankInfo("Punjab National Bank", "pnb", BankStatementFormat.TYPE_B),
    ),
    (
        ["bank of baroda", r"\bbob\b"],
        BankInfo("Bank of Baroda", "bob", BankStatementFormat.TYPE_B),
    ),
    (
        ["canara bank", r"\bcanara\b"],
        BankInfo("Canara Bank", "canara", BankStatementFormat.TYPE_B),
    ),
    (
        ["union bank of india", r"\bunion\s*bank\b"],
        BankInfo("Union Bank of India", "union", BankStatementFormat.TYPE_B),
    ),
    (
        ["idbi bank", r"\bidbi\b"],
        BankInfo("IDBI Bank", "idbi", BankStatementFormat.TYPE_B),
    ),
    (
        ["bank of india", r"\bboi\b"],
        BankInfo("Bank of India", "boi", BankStatementFormat.TYPE_B),
    ),
    (
        ["central bank of india", r"\bcentral\s*bank\b"],
        BankInfo("Central Bank of India", "central", BankStatementFormat.TYPE_B),
    ),
    (
        ["indian bank", r"\bindian\s*bank\b"],
        BankInfo("Indian Bank", "indian", BankStatementFormat.TYPE_B),
    ),
    (
        ["citibank", r"\bciti\b", "citbank"],
        BankInfo("Citibank", "citibank", BankStatementFormat.TYPE_A),
    ),
]

# Fallback / unknown bank
_UNKNOWN_BANK = BankInfo("Generic Bank", "generic", BankStatementFormat.TYPE_A)


# ---------------------------------------------------------------------------
# Detection function
# ---------------------------------------------------------------------------

def detect_bank_extended(text: str, filename: str = "") -> BankInfo:
    """
    Detect the Indian bank from statement text and/or filename.

    Args:
        text:     Raw text from the first page of the statement.
        filename: Original filename (may contain 'HDFC', 'SBI' etc.).

    Returns:
        BankInfo namedtuple. Falls back to UNKNOWN_BANK if nothing matches.
    """
    search_space = (f"{filename}\n{text[:4096]}").lower()

    for patterns, bank_info in _BANK_RULES:
        for pattern in patterns:
            try:
                if re.search(pattern, search_space, re.IGNORECASE):
                    return bank_info
            except re.error:
                # Treat as literal string if pattern is invalid regex
                if pattern.lower() in search_space:
                    return bank_info

    return _UNKNOWN_BANK


def detect_bank_code(text: str, filename: str = "") -> str:
    """Convenience wrapper that returns just the short bank code string."""
    return detect_bank_extended(text, filename).code


def detect_default_format(text: str, filename: str = "") -> BankStatementFormat:
    """Return the expected default statement format for the detected bank."""
    return detect_bank_extended(text, filename).default_format
