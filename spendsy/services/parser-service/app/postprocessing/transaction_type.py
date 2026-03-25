"""
TransactionTypeClassifier — classifies bank transactions by type based on narration.
Types: UPI, NEFT, RTGS, IMPS, ATM, POS, CHQ, NACH, INT, CHRG, OTHERS
"""
from __future__ import annotations

import re

TYPE_PATTERNS: dict[str, list[str]] = {
    "UPI":  [r"\bUPI\b", r"UPI/", r"@\w+"],
    "NEFT": [r"\bNEFT\b", r"NEFT/"],
    "RTGS": [r"\bRTGS\b", r"RTGS/"],
    "IMPS": [r"\bIMPS\b", r"IMPS/"],
    "ATM":  [r"\bATM\b", r"\bATW\b", r"CASH WDL", r"CASH WITHDRAWAL"],
    "POS":  [r"\bPOS\b", r"\bECOM\b", r"\bPURCHASE\b"],
    "CHQ":  [r"\bCLG\b", r"\bCLRG\b", r"\bCHEQUE\b", r"\bCHQ\b", r"CLEARING"],
    "NACH": [r"\bNACH\b", r"\bECS\b", r"\bSI\b"],
    "INT":  [r"\bINTEREST\b", r"INT CR", r"INT PAID", r"INT\.?\s*CREDIT"],
    "CHRG": [r"\bCHARGES\b", r"\bFEE\b", r"\bGST\b", r"SERVICE CHG", r"ANN\s*FEE"],
}

_COMPILED: dict[str, list[re.Pattern]] = {
    k: [re.compile(p, re.IGNORECASE) for p in patterns]
    for k, patterns in TYPE_PATTERNS.items()
}


class TransactionTypeClassifier:
    @staticmethod
    def classify(description: str) -> str:
        """Return the transaction type string for a narration/description."""
        if not description:
            return "OTHERS"
        upper = description.upper()
        for txn_type, patterns in _COMPILED.items():
            for pattern in patterns:
                if pattern.search(upper):
                    return txn_type
        return "OTHERS"
