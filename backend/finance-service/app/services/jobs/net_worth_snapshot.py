"""Daily net-worth snapshot job.

For every user with any finance data, write exactly one
`NetWorthSnapshot` row per calendar day. Re-running the job on the
same day is a no-op for users who already have a snapshot.

Composition:
    assets      = sum(WealthItem.amount where type='asset')
                + max(0, net account balance from Transactions)
    liabilities = sum(WealthItem.amount where type='liability')
                + sum(Loan.remaining_balance)
                + sum(CreditCard.outstanding_balance)
    net_worth   = assets - liabilities

Stored as Numeric(15,2). Rounded to 2 decimals before insert.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Iterable

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import CreditCard, Loan, NetWorthSnapshot, Transaction, WealthItem

logger = logging.getLogger("finance.jobs.net_worth")


def _candidate_user_ids(db: Session) -> Iterable[int]:
    """Every user with at least one finance row worth snapshotting."""
    seen: set[int] = set()
    for model in (Transaction, WealthItem, Loan, CreditCard):
        rows = db.query(distinct(model.user_id)).all()
        for (uid,) in rows:
            if uid is not None:
                seen.add(int(uid))
    return sorted(seen)


def _snapshot_for_user(db: Session, user_id: int, snapshot_date: date) -> bool:
    """Compute and insert a snapshot for the user. Returns True if a row was written."""
    existing = (
        db.query(NetWorthSnapshot)
        .filter(
            NetWorthSnapshot.user_id == user_id,
            NetWorthSnapshot.date == snapshot_date,
        )
        .first()
    )
    if existing is not None:
        return False  # Already snapshotted today

    # Wealth items
    asset_total = db.query(func.coalesce(func.sum(WealthItem.amount), 0)).filter(
        WealthItem.user_id == user_id, WealthItem.type == "asset"
    ).scalar() or 0
    liability_items = db.query(func.coalesce(func.sum(WealthItem.amount), 0)).filter(
        WealthItem.user_id == user_id, WealthItem.type == "liability"
    ).scalar() or 0

    # Cash balance from transactions (income - expense). Only counted as an
    # asset if positive, to avoid double-subtracting when the user is in
    # deficit (they'd already show up via liabilities anyway).
    income = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id, Transaction.type == "income", Transaction.is_transfer.is_(False)
    ).scalar() or 0
    expense = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id, Transaction.type == "expense", Transaction.is_transfer.is_(False)
    ).scalar() or 0
    cash_balance = max(Decimal(income) - Decimal(expense), Decimal(0))

    # Loans
    loan_balance = db.query(func.coalesce(func.sum(Loan.remaining_balance), 0)).filter(
        Loan.user_id == user_id
    ).scalar() or 0

    # Credit cards — `outstanding_balance` column added in migration 20260423_01.
    # Use getattr-via-sql to avoid a hard crash if the migration hasn't been
    # applied yet on this environment.
    try:
        cc_balance = db.query(func.coalesce(func.sum(CreditCard.outstanding_balance), 0)).filter(
            CreditCard.user_id == user_id
        ).scalar() or 0
    except Exception:
        cc_balance = 0

    total_assets = Decimal(asset_total) + cash_balance
    total_liabilities = Decimal(liability_items) + Decimal(loan_balance) + Decimal(cc_balance)
    net_worth = total_assets - total_liabilities

    row = NetWorthSnapshot(
        user_id=user_id,
        date=snapshot_date,
        total_assets=round(total_assets, 2),
        total_liabilities=round(total_liabilities, 2),
        net_worth=round(net_worth, 2),
    )
    db.add(row)
    return True


def run_daily_net_worth_snapshot() -> None:
    """Entry point called by the scheduler."""
    today = date.today()
    written = 0
    skipped = 0
    errored = 0

    db = SessionLocal()
    try:
        for user_id in _candidate_user_ids(db):
            try:
                did_write = _snapshot_for_user(db, user_id, today)
                if did_write:
                    written += 1
                else:
                    skipped += 1
            except Exception:
                errored += 1
                logger.exception("net_worth_snapshot: user %s failed", user_id)
                db.rollback()
                # Continue — one bad user shouldn't block the others.
        db.commit()
    finally:
        db.close()

    logger.info(
        "net_worth_snapshot complete: date=%s written=%d skipped=%d errored=%d",
        today, written, skipped, errored,
    )
