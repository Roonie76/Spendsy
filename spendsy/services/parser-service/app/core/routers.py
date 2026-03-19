from __future__ import annotations
import logging
from enum import Enum
from app.core.quality import ContentQuality

logger = logging.getLogger(__name__)

class ParsingStrategy(str, Enum):
    REGEX = "REGEX"
    LLM = "LLM"
    HYBRID = "HYBRID"
    TABULAR = "TABULAR"

class ParsingRouter:
    def route(self, quality: ContentQuality, filename: str) -> ParsingStrategy:
        filename = filename.lower()
        
        # CSV and XLSX are always handled by Table parser
        if filename.endswith((".csv", ".xlsx", ".xls")):
            logger.info("Routing to TABULAR strategy for tabular file format")
            return ParsingStrategy.TABULAR
            
        if quality == ContentQuality.STRUCTURED:
            logger.info("Routing to REGEX strategy based on quality=STRUCTURED")
            return ParsingStrategy.REGEX
        elif quality == ContentQuality.SEMI_STRUCTURED:
            logger.info("Routing to HYBRID strategy based on quality=SEMI_STRUCTURED")
            return ParsingStrategy.HYBRID
        else:
            logger.info("Routing to LLM strategy based on quality=UNSTRUCTURED")
            return ParsingStrategy.LLM
