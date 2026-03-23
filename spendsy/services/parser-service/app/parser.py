"""
DEPRECATED: app/parser.py is being phased out in favor of modular components in app/core/ and app/parsers/.
This file remains as a bridge for backward compatibility but all logic has been moved.
"""
from __future__ import annotations

import logging
import io
import pdfplumber
import pytesseract

# Re-export from new modular locations
from app.core.schemas import ParsedTransaction, ParserResponse
from app.parsers.llm_parser import LLMParser
from app.parsers.tabular_parser import TabularParser as IntegratedParser

logger = logging.getLogger(__name__)

def detect_bank(first_page_text: str) -> str:
    """Legacy bank detection — use app.parsers.bank_detector instead."""
    from app.parsers.bank_detector import detect_bank_extended
    return detect_bank_extended(first_page_text).code
