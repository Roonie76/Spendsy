from __future__ import annotations

import abc
import logging
from typing import Any

from app.core.schemas import ParserResponse

logger = logging.getLogger(__name__)

class BaseParser(abc.ABC):
    """
    Abstract Base Class for all bank statement parsers.
    Enforces a consistent interface for parsing and returns structured metadata.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Machine-friendly name of the parser."""
        pass

    @property
    @abc.abstractmethod
    def version(self) -> str:
        """Version of the parser logic."""
        pass

    @property
    def priority(self) -> int:
        """Priority of the parser (lower is higher priority). Default is 100."""
        return 100

    @abc.abstractmethod
    def can_handle(self, content: bytes, text: str, **kwargs: Any) -> float:
        """
        Return a confidence score (0.0 to 1.0) indicating how well this parser 
        can handle the document before actually parsing it.
        """
        pass

    @abc.abstractmethod
    def parse(self, content: bytes, text: str, **kwargs: Any) -> ParserResponse:
        """
        Execute parsing on the given content.
        
        Args:
            content: Raw bytes of the document (PDF/CSV/XLSX).
            text: Extracted text from the document.
            **kwargs: Additional metadata (filename, content_type, bank, etc.)
            
        Returns:
            ParserResponse containing transactions and metadata.
        """
        pass

    def confidence(self, transactions: list[Any], **kwargs: Any) -> float:
        """
        Calculate an overall confidence score for the parsed result.
        Default implementation returns 1.0 or based on provided transactions.
        """
        if not transactions:
            return 0.0
    def warmup(self) -> bool:
        """
        Optional: Pre-load models/connections to avoid cold-start latency.
        Returns True if warmup was performed, False otherwise.
        """
        return False
