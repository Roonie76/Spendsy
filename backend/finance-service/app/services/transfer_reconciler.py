"""transfer_reconciler.py
========================

Detect inter-account transfer pairs — most commonly a credit card bill
payment made from a debit account. Without this, the same rupees are
counted twice:

  Debit statement:  -1,00,000 "Credit Card Payment"      (expense)
  Credit statement: +1,00,000 "Payment Received, Thank You" (income)

…while the real expenses on the credit card statement (the actual
purchases) are also already counted. Net result: spend inflated by the
payment amount, income inflated by the payment amount.

This module finds matching pairs and flags both sides as transfers so
dashboards can exclude them. Original rows are preserved for the ledger
view.

Design constraints (intentional):
  - Conservative: keyword-gated. A row only becomes a transfer candidate
    if its description contains explicit CC-payment language. This
    minimizes false positives at the cost of missing some transfers —
    the user can mark these manually via the edit modal.
  - Non-destructive: we never modify the `type`, `amount`, or `date`
    of a row. We only set `is_transfer=True` and `transfer_group_id`.
  - Idempotent: running it twice produces the same result. Already-
    linked rows are not re-matched.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Transaction

log = logging.getLogger("finance.transfer_reconciler")

# Match window — credit card payments typically post within a few business
# days of the debit-side withdrawal.
MATCH_DATE_WINDOW_DAYS = 5

# Amount tolerance — exact rupee match OR within 1% (covers micro-rounding
# on some bank statements).
AMOUNT_TOLERANCE_PCT = Decimal("0.01")

# Keywords that identify the debit-side (outgoing) leg of a CC payment.
# These fire on the raw description before title normalisation.
DEBIT_SIDE_RE = re.compile(
    r"\b("
    r"credit\s*card\s*(?:payment|bill)"
    r"|cc\s*payment"
    r"|card\s*payment"
    r"|bill\s*payment"
    r"|creditcard"
    r")\b",
    re.IGNORECASE,
)

# Keywords that identify the credit-side (incoming) leg as seen on the
# credit card statement itself.
CREDIT_SIDE_RE = re.compile(
    r"\b("
    r"payment\s*received"
    r"|payment\s*thank\s*you"
    r"|thank\s*you\s*for\s*your\s*payment"
    r"|autopay\s*received"
    r"|credit\s*card\s*payment"
    r"|neft\s*received"
    r"|imps\s*received"
    r")\b",
    re.IGNORECASE,
)


@dataclass
class ReconcileResult:
    """Summary of one reconciliation pass."""
    pairs_linked: int = 0
    ambiguous: int = 0  # candidate debits with >1 possible credit match
    # Per-pair detail so the caller can surface a toast / audit log.
    linked_ids: list[tuple[int, int]] = None

    def __post_init__(self):
        if self.linked_ids is None:
            self.linked_ids = []


def _description_for(tx: Transaction) -> str:
    return (tx.raw_description or tx.title or "").strip()


def _is_debit_side_candidate(tx: Transaction) -> bool:
    if tx.is_transfer or tx.transfer_group_id:
        return False
    if tx.type != "expense":
        return False
    return bool(DEBIT_SIDE_RE.search(_description_for(tx)))


def _is_credit_side_candidate(tx: Transaction) -> bool:
    if tx.is_transfer or tx.transfer_group_id:
        return False
    if tx.type != "income":
        return False
    # On the credit card statement, the payment arrives as an income-type row.
    # We require account_type == credit to avoid matching a debit savings
    # deposit that happens to share the word "payment".
    if (tx.account_type or "").lower() != "credit":
        return False
    return bool(CREDIT_SIDE_RE.search(_description_for(tx)))


def _amounts_match(a: Decimal, b: Decimal) -> bool:
    if a == b:
        return True
    if a <= 0 or b <= 0:
        return False
    # Within ±1% of the larger side.
    larger = max(a, b)
    diff = abs(a - b)
    return (diff / larger) <= AMOUNT_TOLERANCE_PCT


def _dates_within_window(a: date, b: date) -> bool:
    return abs((a - b).days) <= MATCH_DATE_WINDOW_DAYS


def detect_transfer_pairs(db: Session, user_id: int) -> ReconcileResult:
    """Scan the user's un-paired candidates and link matching pairs.

    Runs a full pass over all unpaired candidates for the user. Safe to call
    repeatedly — only unpaired rows with matching keywords are considered.
    """
    result = ReconcileResult()

    candidates = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_transfer.is_(False),
            Transaction.transfer_group_id.is_(None),
            or_(
                Transaction.type == "expense",
                Transaction.type == "income",
            ),
        )
        .all()
    )

    debits = [t for t in candidates if _is_debit_side_candidate(t)]
    credits = [t for t in candidates if _is_credit_side_candidate(t)]
    if not debits or not credits:
        return result

    used_credit_ids: set[int] = set()

    for d in debits:
        matches = [
            c for c in credits
            if c.id not in used_credit_ids
            and _amounts_match(Decimal(str(d.amount)), Decimal(str(c.amount)))
            and _dates_within_window(d.date, c.date)
        ]

        if not matches:
            continue

        if len(matches) > 1:
            # Ambiguous — pick the one closest in date, but flag it.
            result.ambiguous += 1
            matches.sort(key=lambda c: abs((c.date - d.date).days))

        chosen = matches[0]
        group_id = str(uuid.uuid4())

        d.transfer_group_id = group_id
        d.is_transfer = True
        chosen.transfer_group_id = group_id
        chosen.is_transfer = True

        used_credit_ids.add(chosen.id)
        result.pairs_linked += 1
        result.linked_ids.append((d.id, chosen.id))

    if result.pairs_linked:
        log.info(
            "transfer_reconcile user_id=%s pairs=%d ambiguous=%d",
            user_id, result.pairs_linked, result.ambiguous,
        )

    return result


def unlink_transfer_group(db: Session, user_id: int, group_id: str) -> int:
    """Remove transfer classification from both sides of a group. Returns
    the number of rows updated. Does not delete the transactions."""
    rows = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transfer_group_id == group_id,
        )
        .all()
    )
    for r in rows:
        r.transfer_group_id = None
        r.is_transfer = False
    return len(rows)


def unlink_peer_on_delete(db: Session, user_id: int, group_id: str, deleted_id: int) -> None:
    """When one side of a transfer is deleted, the other side is no longer
    validly a transfer — clear its flag so it goes back to normal
    spend/income aggregation."""
    if not group_id:
        return
    peers = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.transfer_group_id == group_id,
            Transaction.id != deleted_id,
        )
        .all()
    )
    for p in peers:
        p.transfer_group_id = None
        p.is_transfer = False
