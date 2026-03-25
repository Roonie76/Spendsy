"""
Deduplicator — removes duplicate transactions parsed from overlapping PDF pages or repeated rows.
Uses a stable fingerprint based on: date + description prefix + debit + credit + balance.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _fingerprint(txn: Any) -> str:
    """Build a stable hash for a transaction-like object or dict."""
    date_str = str(getattr(txn, "date", txn.get("date", "") if isinstance(txn, dict) else ""))
    desc     = str(getattr(txn, "description", txn.get("description", "") if isinstance(txn, dict) else ""))[:30]
    debit    = str(getattr(txn, "debit",   txn.get("debit", 0)   if isinstance(txn, dict) else 0) or 0)
    credit   = str(getattr(txn, "credit",  txn.get("credit", 0)  if isinstance(txn, dict) else 0) or 0)
    balance  = str(getattr(txn, "balance", txn.get("balance", 0) if isinstance(txn, dict) else 0) or 0)
    raw = f"{date_str}|{desc}|{debit}|{credit}|{balance}"
    return hashlib.md5(raw.encode()).hexdigest()


class Deduplicator:
    @staticmethod
    def deduplicate(transactions: list) -> list:
        """Return transactions with duplicates removed. Preserves insertion order."""
        seen: set[str] = set()
        unique = []
        for txn in transactions:
            sig = _fingerprint(txn)
            if sig not in seen:
                seen.add(sig)
                unique.append(txn)
            else:
                logger.debug("Deduplicator: duplicate dropped — %s", sig)
        return unique
