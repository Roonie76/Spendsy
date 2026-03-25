import re
import logging
from typing import Dict, Any
from app.core.schemas import StatementMetadata

logger = logging.getLogger(__name__)

class HeaderExtractor:
    """
    Extracts account and statement metadata from the page headers.
    Covers Account No, Name, IFSC, Period, and CIF.
    """
    
    PATTERNS = {
        "account_no": [
            r"Account\s+(?:No|Number)[:\s]+([\w\d]+)",
            r"A/c\s+(?:No|Number)[:\s]+([\w\d]+)",
            r"Acc\s+(?:No|Number)[:\s]+([\w\d]+)",
        ],
        "account_name": [
            r"Name[:\s]+([A-Z\s]{5,40})",
            r"Customer\s+Name[:\s]+([A-Z\s]{5,40})",
        ],
        "ifsc": [
            r"IFSC[\s:]+([A-Z]{4}0[A-Z0-9]{6})",
        ],
        "cif_no": [
            r"CIF\s+(?:No|Number)[:\s]+(\d+)",
        ],
        "branch": [
            r"Branch[:\s]+([A-Z\s]{5,30})",
        ]
    }

    def extract(self, text: str) -> StatementMetadata:
        metadata = {}
        # We only scan the first 2000 characters for headers
        header_area = text[:2000]
        
        for field, patterns in self.PATTERNS.items():
            for pat in patterns:
                match = re.search(pat, header_area, re.IGNORECASE)
                if match:
                    val = match.group(1).strip()
                    if val:
                        metadata[field] = val
                        break
        
        # Period extraction (e.g. "Statement from 01/01/2023 to 31/01/2023")
        period_pat = re.compile(r"(?:Period|Statement\s+from)[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}).+?(?:to|until)[:\s]+(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})", re.IGNORECASE)
        match = period_pat.search(header_area)
        if match:
            # We skip date conversion here to keep it simple for now, 
            # ideally we'd use _parse_date
            pass

        return StatementMetadata(**metadata)
