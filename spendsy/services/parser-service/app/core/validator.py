"""
Validation Layer — per-transaction validation and flagging.

This module sits AFTER the reconciliation engine and provides:
    1. Balance consistency check  (prev+credit-debit = next)
    2. Duplicate detection         (same date + amount + description)
    3. Missing field detection     (null date / amount / description)
    4. Confidence-based flagging   (low confidence transactions)

Each transaction gets a `validation_flags` list and an `is_valid` boolean
that summarises the overall health.

Design principle:
    - Never mutate the original list; return new copies.
    - Prefer flagging over silent dropping — let the caller decide.
    - Use Decimal arithmetic to avoid float rounding errors.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Flag constants
# ---------------------------------------------------------------------------

class Flag:
    MISSING_DATE        = "MISSING_DATE"
    MISSING_AMOUNT      = "MISSING_AMOUNT"
    MISSING_DESCRIPTION = "MISSING_DESCRIPTION"
    DUPLICATE           = "DUPLICATE"
    BALANCE_MISMATCH    = "BALANCE_MISMATCH"
    LOW_CONFIDENCE      = "LOW_CONFIDENCE"
    ZERO_AMOUNT         = "ZERO_AMOUNT"
    NEGATIVE_BALANCE    = "NEGATIVE_BALANCE"


# ---------------------------------------------------------------------------
# Result schema
# ---------------------------------------------------------------------------

@dataclass
class TransactionValidation:
    """Validation outcome for a single transaction."""
    index: int
    flags: list[str] = field(default_factory=list)
    is_valid: bool = True
    expected_balance: float | None = None


@dataclass
class ValidationResult:
    """Aggregate validation result for the full transaction list."""
    total: int
    valid_count: int
    invalid_count: int
    duplicate_count: int
    balance_error_count: int
    validations: list[TransactionValidation]
    overall_score: float   # 0.0 – 1.0


# ---------------------------------------------------------------------------
# Main validator class
# ---------------------------------------------------------------------------

class TransactionValidator:
    """
    Validates a list of parsed transactions and attaches flags to each.

    Usage:
        validator = TransactionValidator()
        result = validator.validate(transactions)
    """

    # Tolerance for balance consistency (INR 0.50 rounding tolerance)
    BALANCE_TOLERANCE = Decimal("0.50")

    # Confidence below this → flag as LOW_CONFIDENCE
    LOW_CONFIDENCE_THRESHOLD = 0.70

    def validate(self, transactions: list[Any]) -> ValidationResult:
        """
        Validate a list of ParsedTransaction-like objects.

        Args:
            transactions: List of objects with attributes:
                          date, description, amount, type, debit, credit,
                          balance, confidence, is_valid

        Returns:
            ValidationResult with per-transaction ValidationOutcome.
        """
        if not transactions:
            return ValidationResult(
                total=0, valid_count=0, invalid_count=0,
                duplicate_count=0, balance_error_count=0,
                validations=[], overall_score=1.0,
            )

        validations: list[TransactionValidation] = []
        duplicate_keys: dict[tuple, int] = {}   # key → first index
        balance_errors = 0

        # ---- Pass 1: Per-transaction field checks + duplicate detection ----
        for idx, tx in enumerate(transactions):
            vld = TransactionValidation(index=idx)

            # Missing field checks
            if not getattr(tx, "date", None):
                vld.flags.append(Flag.MISSING_DATE)

            amt = getattr(tx, "amount", None)
            if amt is None:
                vld.flags.append(Flag.MISSING_AMOUNT)
            elif float(amt) == 0.0:
                vld.flags.append(Flag.ZERO_AMOUNT)

            desc = getattr(tx, "description", None)
            if not desc or not str(desc).strip():
                vld.flags.append(Flag.MISSING_DESCRIPTION)

            # Low confidence
            conf = getattr(tx, "confidence", None)
            if conf is not None and float(conf) < self.LOW_CONFIDENCE_THRESHOLD:
                vld.flags.append(Flag.LOW_CONFIDENCE)

            # Negative balance
            bal = getattr(tx, "balance", None)
            if bal is not None and float(bal) < 0:
                vld.flags.append(Flag.NEGATIVE_BALANCE)

            # Duplicate detection
            date_str = str(getattr(tx, "date", ""))
            desc_str = str(desc or "")[:60].lower().strip()
            amt_cents = int(round(float(amt or 0) * 100))
            dup_key = (date_str, desc_str, amt_cents)

            if dup_key in duplicate_keys:
                vld.flags.append(Flag.DUPLICATE)
                # Also flag the first occurrence
                first_idx = duplicate_keys[dup_key]
                if Flag.DUPLICATE not in validations[first_idx].flags:
                    validations[first_idx].flags.append(Flag.DUPLICATE)
            else:
                duplicate_keys[dup_key] = idx

            vld.is_valid = len(vld.flags) == 0
            validations.append(vld)

        # ---- Pass 2: Balance consistency check ----
        # Only run if we have at least 2 transactions with balance values
        txns_with_balance = [
            (i, tx) for i, tx in enumerate(transactions)
            if getattr(tx, "balance", None) is not None
        ]

        if len(txns_with_balance) >= 2:
            prev_balance: Decimal | None = None

            # Infer starting balance from the first transaction
            first_idx, first_tx = txns_with_balance[0]
            first_bal = self._to_dec(getattr(first_tx, "balance", None))
            first_amt = self._to_dec(getattr(first_tx, "amount", None)) or Decimal("0")
            first_type = getattr(first_tx, "type", "expense")

            if first_bal is not None:
                if first_type == "income":
                    prev_balance = first_bal - first_amt
                else:
                    prev_balance = first_bal + first_amt

            for i, tx in txns_with_balance[1:]:
                if prev_balance is None:
                    break

                credit = self._to_dec(getattr(tx, "credit", None)) or Decimal("0")
                debit  = self._to_dec(getattr(tx, "debit", None))  or Decimal("0")
                actual_balance = self._to_dec(getattr(tx, "balance", None))

                if actual_balance is None:
                    continue

                expected = prev_balance + credit - debit
                diff = abs(actual_balance - expected)

                if diff > self.BALANCE_TOLERANCE:
                    validations[i].flags.append(Flag.BALANCE_MISMATCH)
                    validations[i].expected_balance = float(expected)
                    validations[i].is_valid = False
                    balance_errors += 1
                    logger.debug(
                        "validator: balance_mismatch idx=%d expected=%.2f actual=%.2f diff=%.2f",
                        i, float(expected), float(actual_balance), float(diff),
                    )

                prev_balance = actual_balance

        # ---- Aggregate ----
        invalid_count = sum(1 for v in validations if not v.is_valid)
        dup_count = sum(1 for v in validations if Flag.DUPLICATE in v.flags)
        valid_count = len(validations) - invalid_count
        score = valid_count / len(validations) if validations else 1.0

        logger.info(
            "validator: total=%d valid=%d invalid=%d duplicates=%d balance_errors=%d score=%.4f",
            len(transactions), valid_count, invalid_count, dup_count, balance_errors, score,
        )

        return ValidationResult(
            total=len(transactions),
            valid_count=valid_count,
            invalid_count=invalid_count,
            duplicate_count=dup_count,
            balance_error_count=balance_errors,
            validations=validations,
            overall_score=round(score, 4),
        )

    def apply_flags(self, transactions: list[Any], result: ValidationResult) -> list[Any]:
        """
        Return a new list of transactions with `validation_flags` and `is_valid`
        updated according to the ValidationResult.

        This is a non-destructive operation — original objects are not modified.
        """
        updated = []
        for tx, vld in zip(transactions, result.validations):
            try:
                # Use model_copy if it's a Pydantic model, else fall back to dataclass copying
                if hasattr(tx, "model_copy"):
                    updated.append(tx.model_copy(update={
                        "validation_flags": vld.flags,
                        "is_valid": vld.is_valid,
                    }))
                else:
                    # For plain dataclass objects
                    import copy
                    tx_copy = copy.copy(tx)
                    tx_copy.validation_flags = vld.flags
                    tx_copy.is_valid = vld.is_valid
                    updated.append(tx_copy)
            except Exception:
                updated.append(tx)
        return updated

    @staticmethod
    def _to_dec(val: Any) -> Decimal | None:
        if val is None:
            return None
        try:
            return Decimal(str(val))
        except (InvalidOperation, TypeError, ValueError):
            return None
