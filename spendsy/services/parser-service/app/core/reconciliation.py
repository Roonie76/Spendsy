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
from app.core.schemas import ParserResponse

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


class CrossParserReconciler:
    """
    Compares multiple ParserResponses and selects the best one based on:
    1. Highest reconciliation_score (balance check)
    2. Highest transaction count (if reconciliation_scores are similar)
    3. Lowest number of validation errors
    """
    def reconcile_multi(self, responses: List[ParserResponse]) -> ParserResponse:
        if not responses:
            return ParserResponse(status="error", transactions=[], reconciliation_score=0.0, meta={})
            
        # Filter out errors
        valid_responses = [r for r in responses if r.status in ("success", "no_transactions")]
        if not valid_responses:
            return responses[0] # Return the first error if all failed
            
        def rank_key(res: ParserResponse):
            has_txns = 1 if len(res.transactions) > 0 else 0
            score = res.reconciliation_score or 0.0
            count = len(res.transactions)
            val_meta = res.meta.get("validation") or {}
            validation_score = val_meta.get("overall_score") if isinstance(val_meta, dict) else 0.0
            if validation_score is None: validation_score = 0.0
            # Bias towards higher precision deterministic parsers if needed
            parser_bonus = 0.0 
            return (has_txns, score, validation_score + parser_bonus, count)
            
        valid_responses.sort(key=rank_key, reverse=True)
        
        # ENHANCEMENT: If we have multiple high-quality results, try to merge them
        if len(valid_responses) >= 2:
            top = valid_responses[0]
            second = valid_responses[1]
            
            # If both are verified (score > 0.9) and have balanced results
            if top.reconciliation_score > 0.9 and second.reconciliation_score > 0.9:
                logger.info("SmartMerger: Attempting to merge top 2 parser results")
                merger = TransactionMerger()
                merged_txns = merger.merge(top.transactions, second.transactions)
                
                # Create a new response with merged transactions
                merged_res = top.model_copy(update={
                    "transactions": merged_txns,
                    "meta": {**top.meta, "is_merged": True, "merged_with": second.meta.get("method", "unknown")}
                })
                # Re-calculate reconciliation score for merged result
                recon = ReconciliationEngine().reconcile(merged_txns)
                merged_res.reconciliation_score = recon.reconciliation_score
                return merged_res

        winner = valid_responses[0]
        # Backward compatibility: Ensure bank is in meta
        if "bank" not in winner.meta and winner.statement_metadata.bank_name:
            winner.meta["bank"] = winner.statement_metadata.bank_name
            
        logger.info(
            "cross_parser_reconciliation status=complete winner=%s score=%.4f txns=%d",
            winner.meta.get("method") or winner.meta.get("parser_name"),
            winner.reconciliation_score,
            len(winner.transactions)
        )
        return winner


class TransactionMerger:
    """
    Intelligently aligns and merges two lists of transactions.
    Used to combine strengths of different parsers (e.g., Tabular + Regex).
    """
    def merge(self, base: List[Any], secondary: List[Any]) -> List[Any]:
        if not secondary: return base
        if not base: return secondary
        
        # 1. Simple heuristic: if one has significantly more transactions and is verified, prefer it
        if len(base) > len(secondary) * 1.5: return base
        if len(secondary) > len(base) * 1.5: return secondary
        
        # 2. Alignment based Merge (Advanced)
        # For now, we perform a simple union based on Date + Amount + Desc similarity
        merged = []
        seen_keys = set()
        
        for tx in base:
            key = self._gen_key(tx)
            merged.append(tx)
            seen_keys.add(key)
            
        for tx in secondary:
            key = self._gen_key(tx)
            if key not in seen_keys:
                # Potential new transaction found by secondary parser
                # Fuzzy check to avoid adding minor variations of same transaction
                if not self._is_fuzzy_duplicate(tx, merged):
                    merged.append(tx)
        
        # Re-sort by date
        merged.sort(key=lambda x: str(x.date))
        return merged

    def _gen_key(self, tx: Any) -> tuple:
        date_str = str(getattr(tx, "date", ""))
        amt_cents = int(round(float(getattr(tx, "amount", 0) or 0) * 100))
        # Use first 20 chars of desc to avoid multi-line variation issues
        desc_start = str(getattr(tx, "description", ""))[:20].lower().strip()
        return (date_str, amt_cents, desc_start)

    def _is_fuzzy_duplicate(self, tx: Any, candidates: List[Any]) -> bool:
        from fuzzywuzzy import fuzz
        
        tx_date = str(getattr(tx, "date", ""))
        tx_amt = float(getattr(tx, "amount", 0) or 0)
        tx_desc = str(getattr(tx, "description", "")).lower()
        
        for cand in candidates:
            if str(cand.date) == tx_date and abs(float(cand.amount or 0) - tx_amt) < 0.01:
                # Same date and amount, check description similarity
                ratio = fuzz.partial_ratio(tx_desc, str(cand.description).lower())
                if ratio > 80:
                    return True
        return False
