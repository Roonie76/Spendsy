"""
Transaction reconciliation engine.
Validates the sequence of transactions using:
    prev_balance + credit - debit = new_balance
Detects flipped debit/credit, incorrect amounts, and missing transactions.
Attempts high-confidence auto-fixes where possible.
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Any, Dict

logger = logging.getLogger(__name__)

@dataclass
class ReconciliationError:
    index: int
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ReconciliationResult:
    status: str  # "verified" | "flagged"
    errors: List[ReconciliationError]
    corrected_transactions: List[Any]
    reconciliation_score: float

class ReconciliationEngine:
    def __init__(self, precision: int = 2):
        self.precision = precision

    def reconcile(self, transactions: List[Any]) -> ReconciliationResult:
        """
        Perform reconciliation on a list of ParsedTransaction-like objects.
        Returns a ReconciliationResult.
        """
        if not transactions:
            return ReconciliationResult(status="verified", errors=[], corrected_transactions=[], reconciliation_score=1.0)

        errors: List[ReconciliationError] = []
        corrected = [t.model_copy() for t in transactions]
        
        # Sort by date and then try to maintain sequence
        # We assume they are already in extraction order if dates are the same
        
        current_balance: Optional[Decimal] = None
        valid_count = 0
        total_steps = 0

        for i, tx in enumerate(corrected):
            # Convert to Decimal for precise calculation
            amt = self._to_decimal(tx.amount)
            debit = self._to_decimal(tx.debit)
            credit = self._to_decimal(tx.credit)
            balance = self._to_decimal(tx.balance)

            # Ensure debit/credit match amount if only amount was set
            if debit is None and credit is None and amt is not None:
                if tx.type == "expense":
                    debit = amt
                else:
                    credit = amt

            # First transaction: initialize balance if possible
            if current_balance is None:
                if balance is not None:
                    # current_balance + credit - debit = balance
                    # current_balance = balance - credit + debit
                    current_balance = balance - (credit or 0) + (debit or 0)
                    valid_count += 1
                continue

            total_steps += 1
            expected_balance = current_balance + (credit or 0) - (debit or 0)

            if balance is not None:
                diff = abs(balance - expected_balance)
                if diff < Decimal("0.01"):
                    valid_count += 1
                    current_balance = balance
                else:
                    # Mismatch detected. Try to diagnose and fix.
                    fixed = self._attempt_fix(i, tx, current_balance, balance, debit, credit)
                    if fixed:
                        corrected[i] = fixed
                        valid_count += 1
                        current_balance = balance
                        logger.info(f"Auto-fixed transaction at index {i}")
                    else:
                        errors.append(ReconciliationError(
                            index=i,
                            message=f"Balance mismatch: expected {expected_balance}, got {balance}",
                            details={
                                "expected": float(expected_balance),
                                "actual": float(balance),
                                "diff": float(diff)
                            }
                        ))
                        # Update current_balance to the one from the statement to continue
                        current_balance = balance
            else:
                # No balance on this row, follow the expected sequence
                current_balance = expected_balance
                tx.balance = float(current_balance)

        score = valid_count / (total_steps + 1) if total_steps >= 0 else 1.0
        status = "verified" if not errors and score > 0.95 else "flagged"

        return ReconciliationResult(
            status=status,
            errors=errors,
            corrected_transactions=corrected,
            reconciliation_score=round(score, 4)
        )

    def _attempt_fix(self, index: int, tx: Any, prev_balance: Decimal, current_balance: Decimal, 
                     debit: Optional[Decimal], credit: Optional[Decimal]) -> Optional[Any]:
        """
        Heuristics for high-confidence fixes.
        """
        required_delta = current_balance - prev_balance
        
        # 1. Detect flipped Debit/Credit
        # If prev_balance + debit - credit == current_balance
        if abs(prev_balance + (debit or 0) - (credit or 0) - current_balance) < Decimal("0.01"):
            # They are flipped!
            # Wait, prev_balance + credit - debit = current_balance (Correct)
            # If flipping them works:
            pass
            
        # Flip test:
        potential_debit = credit
        potential_credit = debit
        if abs(prev_balance + (potential_credit or 0) - (potential_debit or 0) - current_balance) < Decimal("0.01"):
            tx.debit = float(potential_debit) if potential_debit is not None else None
            tx.credit = float(potential_credit) if potential_credit is not None else None
            tx.type = "income" if potential_credit else "expense"
            tx.amount = float(potential_credit or potential_debit or 0)
            return tx

        # 2. Detect incorrect amount if description suggests a different type
        # Or if one column was blank and the calculated delta matches the other column
        if required_delta > 0:
            # Should be a credit
            if abs(required_delta - (debit or 0)) < Decimal("0.01"):
                # Amount was put in debit instead of credit
                tx.credit = float(required_delta)
                tx.debit = None
                tx.type = "income"
                tx.amount = float(required_delta)
                return tx
        else:
            # Should be a debit (negative delta)
            pos_delta = -required_delta
            if abs(pos_delta - (credit or 0)) < Decimal("0.01"):
                # Amount was put in credit instead of debit
                tx.debit = float(pos_delta)
                tx.credit = None
                tx.type = "expense"
                tx.amount = float(pos_delta)
                return tx

        return None

    def _to_decimal(self, val: Any) -> Optional[Decimal]:
        if val is None:
            return None
        try:
            return Decimal(str(val))
        except (ValueError, InvalidOperation):
            return None
