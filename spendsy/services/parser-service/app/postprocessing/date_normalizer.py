"""
DateNormalizer — safely parses bank statement date strings into Python date objects.
Handles all common Indian bank date formats.
"""
from __future__ import annotations

import re
import logging
from datetime import date, datetime

logger = logging.getLogger(__name__)

# All known Indian bank date formats
ALL_FORMATS = [
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d-%m-%Y",
    "%d-%m-%y",
    "%d %b %Y",
    "%d %B %Y",
    "%d%b%Y",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d-%m-%Y %H:%M:%S",
]

# Strip leading day names: "Mon 01/01/2024" → "01/01/2024"
_DAY_PREFIX = re.compile(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[,\s]+", re.IGNORECASE)


class DateNormalizer:
    def __init__(self, preferred_formats: list[str] | None = None):
        self.formats = preferred_formats or ALL_FORMATS

    def parse(self, date_string: str) -> date | None:
        """Parse a raw date string into a Python date. Returns None on failure."""
        if not date_string or not date_string.strip():
            return None

        s = _DAY_PREFIX.sub("", date_string.strip())

        for fmt in self.formats:
            try:
                return datetime.strptime(s, fmt).date()
            except ValueError:
                continue

        logger.debug("DateNormalizer: could not parse '%s'", date_string)
        return None

    def is_valid(self, date_string: str) -> bool:
        return self.parse(date_string) is not None

    @staticmethod
    def parse_static(date_string: str, preferred_formats: list[str] | None = None) -> date | None:
        return DateNormalizer(preferred_formats).parse(date_string)
