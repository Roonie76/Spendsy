"""
BankIdentifier — identifies the issuing bank from parsed page text using
keyword + regex fingerprints.  Returns a bank_id string (HDFC, SBI, ICICI, …)
or "GENERIC" when no match is found.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class _Fingerprint:
    keywords : list[str]
    patterns : list[str]


# Each entry: keywords → plain case-insensitive substring matches (2 pts each)
#             patterns → compiled regex matches          (3 pts each)
BANK_FINGERPRINTS: dict[str, _Fingerprint] = {
    "HDFC": _Fingerprint(
        keywords=["HDFC Bank", "HDFC BANK LIMITED", "hdfcbank.com"],
        patterns=[r"HDFC0\d{6}", r"A/C\s*No\s*[:\-]\s*\d{10,16}",
                  r"Withdrawal\s*Amt", r"Deposit\s*Amt"],
    ),
    "SBI": _Fingerprint(
        keywords=["State Bank of India", "SBI", "onlinesbi.com", "YONO SBI"],
        patterns=[r"SBIN0[A-Z0-9]{6}", r"Account\s*Number\s*[:\-]\s*\d{11}"],
    ),
    "ICICI": _Fingerprint(
        keywords=["ICICI Bank", "ICICI BANK LIMITED", "icicibank.com"],
        patterns=[r"ICIC0\d{6}", r"Account\s*No\.\s*[:\-]\s*\d{12}",
                  r"Transaction\s*Remarks"],
    ),
    "AXIS": _Fingerprint(
        keywords=["Axis Bank", "AXIS BANK LIMITED", "axisbank.com"],
        patterns=[r"UTIB0\d{6}"],
    ),
    "KOTAK": _Fingerprint(
        keywords=["Kotak Mahindra Bank", "Kotak Bank", "kotak.com"],
        patterns=[r"KKBK0\d{6}"],
    ),
    "YES": _Fingerprint(
        keywords=["Yes Bank", "YES BANK", "yesbank.in"],
        patterns=[r"YESB0\d{6}"],
    ),
    "IDFC": _Fingerprint(
        keywords=["IDFC FIRST Bank", "IDFC First", "idfcfirstbank.com"],
        patterns=[r"IDFB0\d{6}"],
    ),
    "INDUSIND": _Fingerprint(
        keywords=["IndusInd Bank", "indusind.com"],
        patterns=[r"INDB0\d{6}"],
    ),
    "PNB": _Fingerprint(
        keywords=["Punjab National Bank", "PNB", "pnbindia.in"],
        patterns=[r"PUNB0\d{6}"],
    ),
    "BOB": _Fingerprint(
        keywords=["Bank of Baroda", "bankofbaroda.in", "BOB"],
        patterns=[r"BARB0\d{6}"],
    ),
    "CANARA": _Fingerprint(
        keywords=["Canara Bank", "canarabank.com"],
        patterns=[r"CNRB0\d{6}"],
    ),
    "UNION": _Fingerprint(
        keywords=["Union Bank of India", "unionbankofindia"],
        patterns=[r"UBIN0\d{6}"],
    ),
}

# Pre-compile patterns once
_COMPILED: dict[str, list[re.Pattern]] = {
    bank_id: [re.compile(p, re.IGNORECASE) for p in fp.patterns]
    for bank_id, fp in BANK_FINGERPRINTS.items()
}


class BankIdentifier:
    @staticmethod
    def identify(probe_text: str) -> str:
        """
        Score each bank against the first 2 pages of text.
        Returns the highest-scoring bank_id or "GENERIC".
        """
        upper = probe_text.upper()
        scores: dict[str, int] = {}

        for bank_id, fp in BANK_FINGERPRINTS.items():
            score = 0
            for kw in fp.keywords:
                if kw.upper() in upper:
                    score += 2
            for pat in _COMPILED[bank_id]:
                if pat.search(probe_text):
                    score += 3
            scores[bank_id] = score

        best = max(scores, key=lambda k: scores[k])
        if scores[best] == 0:
            logger.info("BankIdentifier: no match → GENERIC")
            return "GENERIC"

        logger.info("BankIdentifier: identified bank=%s score=%d", best, scores[best])
        return best

    @staticmethod
    def identify_from_pages(all_pages_data: list) -> str:
        """Convenience wrapper that pulls text from the first 2 pages."""
        probe = ""
        for page in all_pages_data[:2]:
            probe += getattr(page, "raw_text", "") + "\n"
        return BankIdentifier.identify(probe)
