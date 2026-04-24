"""Nightly proactive-insights engine.

Walks every user and runs a set of deterministic rules against their
recent transactions. Each rule that fires writes a single `UserAlert`
row with `is_read=False` — the frontend picks these up and renders an
unread badge.

Rules (Phase 1 — deterministic, no LLM):
    1. `category_spike`    — any category's last-30-day spend is ≥ 30%
                             higher than its previous 30-day spend AND the
                             shift is at least ₹1,000.
    2. `large_transaction` — any single expense in the last 7 days that's
                             ≥ 3× the user's median expense (floor ₹5,000).
    3. `unusual_merchant`  — a merchant the user hasn't transacted with
                             in the prior 90 days appears 2+ times in the
                             last 7 days. (Signals new subscription or
                             recurring shift.)

De-duplication:
    For each (user_id, alert_type, data_signature), we only write one
    alert per 7-day window. The `data_signature` lives in `data_json`
    and is checked before insert. This prevents the same category spike
    from re-firing every night until the user reads it.

Phase 2 (deferred): LLM-scored anomalies on top of these rules.
"""

from __future__ import annotations

import logging
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Iterable

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import Transaction, UserAlert

logger = logging.getLogger("finance.jobs.insights")

# Tunable thresholds. Kept as module-level constants so they're easy to
# spot and adjust without digging through rule bodies.
CATEGORY_SPIKE_PCT = 0.30
CATEGORY_SPIKE_MIN_DELTA = 1_000
LARGE_TX_MULTIPLIER = 3.0
LARGE_TX_FLOOR = 5_000
UNUSUAL_MERCHANT_LOOKBACK_DAYS = 90
UNUSUAL_MERCHANT_MIN_HITS = 2
DEDUPE_WINDOW_DAYS = 7


def _candidate_user_ids(db: Session) -> Iterable[int]:
    rows = db.query(distinct(Transaction.user_id)).all()
    return sorted({int(uid) for (uid,) in rows if uid is not None})


def _recent_alert_signatures(db: Session, user_id: int) -> set[tuple[str, str]]:
    """All (alert_type, signature) pairs this user saw in the dedupe window."""
    cutoff = datetime.utcnow() - timedelta(days=DEDUPE_WINDOW_DAYS)
    rows = (
        db.query(UserAlert.alert_type, UserAlert.data_json)
        .filter(UserAlert.user_id == user_id, UserAlert.created_at >= cutoff)
        .all()
    )
    return {
        (row[0] or "", (row[1] or {}).get("signature", ""))
        for row in rows
    }


def _emit_alert(
    db: Session,
    user_id: int,
    alert_type: str,
    severity: str,
    title: str,
    description: str,
    signature: str,
    extra_data: dict | None = None,
) -> None:
    """Insert a UserAlert row. Caller is responsible for dedupe checks."""
    data_json = {"signature": signature}
    if extra_data:
        data_json.update(extra_data)
    db.add(UserAlert(
        user_id=user_id,
        alert_type=alert_type,
        severity=severity,
        title=title[:100],
        description=description[:255],
        data_json=data_json,
        is_read=False,
    ))


# ---------------------------------------------------------------------------
# Rule 1 — category spike
# ---------------------------------------------------------------------------


def _check_category_spike(
    db: Session,
    user_id: int,
    today: date,
    seen: set[tuple[str, str]],
) -> int:
    """Compare last-30-day spend per category to prior 30 days."""
    curr_start = today - timedelta(days=30)
    prev_start = today - timedelta(days=60)

    curr_rows = (
        db.query(Transaction.category, func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.is_transfer.is_(False),
            Transaction.date >= curr_start,
            Transaction.date <= today,
        )
        .group_by(Transaction.category)
        .all()
    )
    prev_rows = (
        db.query(Transaction.category, func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.is_transfer.is_(False),
            Transaction.date >= prev_start,
            Transaction.date < curr_start,
        )
        .group_by(Transaction.category)
        .all()
    )
    prev_map = {cat: float(amt) for cat, amt in prev_rows}

    fired = 0
    for cat, amt in curr_rows:
        curr = float(amt)
        prev = prev_map.get(cat, 0.0)
        if prev <= 0:
            continue  # New category — handled separately (phase 2)
        delta = curr - prev
        pct = delta / prev
        if pct < CATEGORY_SPIKE_PCT or delta < CATEGORY_SPIKE_MIN_DELTA:
            continue
        signature = f"category_spike:{cat}"
        if ("spike", signature) in seen:
            continue

        severity = "danger" if pct >= 0.60 else "warning"
        _emit_alert(
            db,
            user_id=user_id,
            alert_type="spike",
            severity=severity,
            title=f"{cat.title()} spending up {int(pct * 100)}%",
            description=f"Last 30 days ₹{curr:,.0f} vs prior ₹{prev:,.0f} (+₹{delta:,.0f}).",
            signature=signature,
            extra_data={"category": cat, "current": curr, "previous": prev, "pct": round(pct, 3)},
        )
        seen.add(("spike", signature))
        fired += 1
    return fired


# ---------------------------------------------------------------------------
# Rule 2 — large single transaction
# ---------------------------------------------------------------------------


def _check_large_transactions(
    db: Session,
    user_id: int,
    today: date,
    seen: set[tuple[str, str]],
) -> int:
    """Flag any expense ≥ 3× the user's median, floor ₹5k."""
    recent_rows = (
        db.query(Transaction.id, Transaction.amount, Transaction.date, Transaction.title, Transaction.category)
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.is_transfer.is_(False),
            Transaction.date >= today - timedelta(days=60),
        )
        .order_by(Transaction.date.desc())
        .all()
    )
    if len(recent_rows) < 10:
        return 0  # Not enough data for a median

    amounts = [float(r.amount) for r in recent_rows]
    median = statistics.median(amounts)
    threshold = max(median * LARGE_TX_MULTIPLIER, LARGE_TX_FLOOR)

    recent_cutoff = today - timedelta(days=7)
    fired = 0
    for row in recent_rows:
        if row.date < recent_cutoff:
            continue
        if float(row.amount) < threshold:
            continue
        signature = f"large_tx:{row.id}"
        if ("large_transaction", signature) in seen:
            continue
        _emit_alert(
            db,
            user_id=user_id,
            alert_type="large_transaction",
            severity="warning",
            title=f"Large {row.category} expense: ₹{float(row.amount):,.0f}",
            description=f"{row.title[:120]} on {row.date.isoformat()} — {float(row.amount)/median:.1f}× your usual.",
            signature=signature,
            extra_data={"tx_id": row.id, "amount": float(row.amount), "median": median},
        )
        seen.add(("large_transaction", signature))
        fired += 1
    return fired


# ---------------------------------------------------------------------------
# Rule 3 — unusual merchant
# ---------------------------------------------------------------------------


def _check_unusual_merchant(
    db: Session,
    user_id: int,
    today: date,
    seen: set[tuple[str, str]],
) -> int:
    """Merchant unseen in last 90 days now appears 2+ times in last 7."""
    recent_start = today - timedelta(days=7)
    lookback_start = today - timedelta(days=UNUSUAL_MERCHANT_LOOKBACK_DAYS)

    recent = (
        db.query(Transaction.title)
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.is_transfer.is_(False),
            Transaction.date >= recent_start,
        )
        .all()
    )
    prior = (
        db.query(Transaction.title)
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == "expense",
            Transaction.is_transfer.is_(False),
            Transaction.date >= lookback_start,
            Transaction.date < recent_start,
        )
        .all()
    )

    def _key(title: str | None) -> str:
        return (title or "").strip().lower()[:60]

    recent_hits = Counter(_key(r.title) for r in recent)
    prior_set = {_key(r.title) for r in prior}

    fired = 0
    for merchant, hits in recent_hits.items():
        if not merchant or hits < UNUSUAL_MERCHANT_MIN_HITS:
            continue
        if merchant in prior_set:
            continue
        signature = f"unusual_merchant:{merchant}"
        if ("unusual_merchant", signature) in seen:
            continue
        _emit_alert(
            db,
            user_id=user_id,
            alert_type="unusual_merchant",
            severity="info",
            title=f"New merchant: {merchant[:40]}",
            description=f"{hits} transactions in last 7 days, none in the 90 days before. New subscription?",
            signature=signature,
            extra_data={"merchant": merchant, "hits_last_7d": hits},
        )
        seen.add(("unusual_merchant", signature))
        fired += 1
    return fired


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_nightly_insights() -> None:
    today = date.today()
    total_fired = 0
    users_processed = 0
    users_errored = 0

    db = SessionLocal()
    try:
        for user_id in _candidate_user_ids(db):
            try:
                seen = _recent_alert_signatures(db, user_id)
                fired = 0
                fired += _check_category_spike(db, user_id, today, seen)
                fired += _check_large_transactions(db, user_id, today, seen)
                fired += _check_unusual_merchant(db, user_id, today, seen)
                total_fired += fired
                users_processed += 1
            except Exception:
                users_errored += 1
                logger.exception("proactive_insights: user %s failed", user_id)
                db.rollback()
        db.commit()
    finally:
        db.close()

    logger.info(
        "proactive_insights complete: date=%s users=%d alerts_fired=%d errored=%d",
        today, users_processed, total_fired, users_errored,
    )
