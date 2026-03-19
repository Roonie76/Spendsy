from __future__ import annotations
import re
import logging
from enum import Enum
from typing import TypedDict

logger = logging.getLogger(__name__)

class ContentQuality(str, Enum):
    STRUCTURED = "STRUCTURED"
    SEMI_STRUCTURED = "SEMI_STRUCTURED"
    UNSTRUCTURED = "UNSTRUCTURED"

class QualityMetrics(TypedDict):
    tabular_density: float
    date_density: float
    amount_density: float
    line_count: int

class QualityDetector:
    # Heuristic patterns
    DATE_PATTERN = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")
    AMOUNT_PATTERN = re.compile(r"\d+[,.]\d{2}\b")
    
    def detect(self, text: str) -> ContentQuality:
        if not text:
            return ContentQuality.UNSTRUCTURED
            
        lines = text.splitlines()
        line_count = len(lines)
        if line_count == 0:
            return ContentQuality.UNSTRUCTURED
            
        date_matches = self.DATE_PATTERN.findall(text)
        amount_matches = self.AMOUNT_PATTERN.findall(text)
        
        date_density = len(date_matches) / line_count if line_count > 0 else 0
        amount_density = len(amount_matches) / line_count if line_count > 0 else 0
        
        # Calculate tabular density (lines that have both a date and an amount)
        tabular_lines = 0
        for line in lines:
            if self.DATE_PATTERN.search(line) and self.AMOUNT_PATTERN.search(line):
                tabular_lines += 1
        
        tabular_density = tabular_lines / line_count if line_count > 0 else 0
        
        logger.info(
            f"Quality analysis: lines={line_count}, dates={len(date_matches)}, "
            f"amounts={len(amount_matches)}, tabular_density={tabular_density:.2f}"
        )
        
        if tabular_density > 0.4:
            return ContentQuality.STRUCTURED
        elif tabular_density > 0.1 or date_density > 0.3:
            return ContentQuality.SEMI_STRUCTURED
        else:
            return ContentQuality.UNSTRUCTURED
