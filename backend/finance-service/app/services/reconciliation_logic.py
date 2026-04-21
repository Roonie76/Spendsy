import logging
from datetime import timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Transaction

logger = logging.getLogger(__name__)

def reconcile_user_transactions(db: Session, user_id: int):
    """
    Find matching Bank Statement "debits" and Credit Card Statement "credits" 
    to prevent double counting of expenses.
    
    Logic:
    - Target: Debits from bank accounts (account_type='debit')
    - Matching: Credits on credit card statements (account_type='credit')
    - Criteria: Same absolute amount, Dates within 4 days, same user_id.
    """
    logger.info(f"Starting reconciliation for user {user_id}")
    
    # 1. Fetch potential bank payments (expenses from debit accounts)
    # We only look at 'active' transactions that aren't already reconciled
    bank_payments = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.account_type == "debit",
            Transaction.type == "expense",
            Transaction.status == "active"
        )
        .all()
    )
    
    # 2. Fetch potential card receipts (income/credits on credit card accounts)
    card_receipts = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.account_type == "credit",
            Transaction.type == "income",
            Transaction.status == "active"
        )
        .all()
    )
    
    reconciled_count = 0
    
    # 3. Match them up
    # This is a basic O(N*M) matching. For typical statement volumes (50-100 txs), this is fine.
    # For massive datasets, we could use a dictionary of {amount: [txs]}
    for bp in bank_payments:
        # Check if already reconciled locally in this loop
        if any(f.get("type") == "reconciliation" for f in (bp.reconciliation_flags or [])):
            continue
            
        for cr in card_receipts:
            # Check if cr already reconciled
            if any(f.get("type") == "reconciliation" for f in (cr.reconciliation_flags or [])):
                continue
                
            # Match amount exactly
            if float(bp.amount) == float(cr.amount):
                # Match date within 4 days
                date_diff = abs((bp.date - cr.date).days)
                if date_diff <= 4:
                    logger.info(f"MATCH FOUND: bank_tx={bp.id} and card_tx={cr.id} | Amount={bp.amount}")
                    
                    # Link them
                    bp_flags = bp.reconciliation_flags or []
                    cr_flags = cr.reconciliation_flags or []
                    
                    bp_flags.append({
                        "type": "reconciliation",
                        "linked_tx_id": cr.id,
                        "linked_tx_uid": cr.uid,
                        "method": "auto_sync",
                        "partner_account_type": "credit"
                    })
                    cr_flags.append({
                        "type": "reconciliation",
                        "linked_tx_id": bp.id,
                        "linked_tx_uid": bp.uid,
                        "method": "auto_sync",
                        "partner_account_type": "debit"
                    })
                    
                    bp.reconciliation_flags = bp_flags
                    cr.reconciliation_flags = cr_flags
                    
                    # BUSINESS LOGIC: Change bank payment to 'transfer' to avoid double-counting
                    # The CC statement already contains the individual expenses.
                    # This bank payment was just the bill payoff.
                    bp.category = "transfer"
                    bp.type = "transfer" # If your system uses 'transfer' as a type
                    
                    reconciled_count += 1
                    break # Move to next bank payment
    
    try:
        db.commit()
        logger.info(f"Reconciliation complete: {reconciled_count} pairs linked.")
    except Exception as e:
        db.rollback()
        logger.error(f"Reconciliation database error: {e}")
        reconciled_count = 0
        
    return reconciled_count
