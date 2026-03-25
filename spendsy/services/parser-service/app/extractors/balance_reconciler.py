"""
BalanceReconciler — cross-validates every transaction's balance against
prev_balance ± txn_amount. Flags drift rows and lowers confidence.

Tolerance: 0.05 INR (handles rounding differences in bank statements).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

logger = logging.getLogger(__name__)

TOLERANCE = Decimal("0.05")


@dataclass
class ReconciliationReport:
    is_clean:        bool = True
    drift_rows:      list[int] = field(default_factory=list)
    errors:          list[str] = field(default_factory=list)
    warnings:        list[str] = field(default_factory=list)
    drift_total:     Decimal = Decimal("0")


class BalanceReconciler:
    @staticmethod
    def reconcile(transactions: list, opening_balance: Decimal | None = None) -> ReconciliationReport:
        report = ReconciliationReport()

        if not transactions:
            return report

        # Seed prev_balance
        prev = opening_balance
        if prev is None:
            # Infer from first transaction
            t0 = transactions[0]
            bal = getattr(t0, "balance", None)
            dr  = getattr(t0, "debit",   None)
            cr  = getattr(t0, "credit",  None)
            if bal is not None:
                if dr:  prev = bal + dr
                elif cr: prev = bal - cr
                else:    prev = bal

        for i, txn in enumerate(transactions):
            bal = getattr(txn, "balance", None)
            dr  = getattr(txn, "debit",   None)
            cr  = getattr(txn, "credit",  None)

            if bal is None or prev is None:
                prev = bal
                continue

            if dr is not None:
                expected = prev - dr
            elif cr is not None:
                expected = prev + cr
            else:
                prev = bal
                continue

            delta = abs(expected - bal)
            if delta > TOLERANCE:
                report.is_clean = False
                report.drift_rows.append(i)
                report.drift_total += delta
                msg = f"Row {i}: expected {expected:.2f}, got {bal:.2f}, delta={delta:.2f}"
                report.errors.append(msg)
                logger.warning("BalanceReconciler drift: %s", msg)
                # Lower confidence on drifting row
                if hasattr(txn, "confidence"):
                    txn.confidence = max(0.0, txn.confidence - 0.5)

            prev = bal

        return report
