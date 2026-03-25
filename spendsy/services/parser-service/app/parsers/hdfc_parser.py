import logging
import re
from typing import Any
from app.parsers.type_a_parser import TypeAParser
from app.core.schemas import ParserResponse

logger = logging.getLogger(__name__)

class HDFCParser(TypeAParser):
    """
    Dedicated parser for HDFC Bank statements.
    Inherits from TypeAParser but adds HDFC-specific cleaning and header logic.
    """
    
    @property
    def name(self) -> str:
        return "hdfc"

    @property
    def version(self) -> str:
        return "1.1.0"

    @property
    def priority(self) -> int:
        return 50 # Higher priority for HDFC files

    def can_handle(self, content: bytes, text: str, **kwargs: Any) -> float:
        t = text.upper()
        if "HDFC BANK" in t or "HDFC STATEMENT" in t:
            base_score = super().can_handle(content, text, **kwargs)
            return max(base_score, 0.98)
        return 0.0

    def parse(self, content: bytes, text: str, **kwargs: Any) -> ParserResponse:
        # We use the base TypeAParser logic
        response = super().parse(content, text, **kwargs)
        
        # Add HDFC-specific post-processing if needed
        if response.status == "success":
            for tx in response.transactions:
                # Example: HDFC often has "UPI-..." or "POS-..." prefixes
                tx.description = re.sub(r"^(?:UPI|POS|ATM)-", "", tx.description).strip()
        
        return response
