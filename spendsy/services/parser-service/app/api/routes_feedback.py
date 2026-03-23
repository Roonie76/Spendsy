from fastapi import APIRouter, Depends, HTTPException
from app.core.schemas import TransactionFeedback
from app.core.internal_auth import verify_internal_api_key
from app.core.categorizer import CorrectionStore
import logging

router = APIRouter(tags=["feedback"])
logger = logging.getLogger(__name__)

@router.post("/feedback/transaction")
async def submit_transaction_feedback(
    feedback: TransactionFeedback,
    _: None = Depends(verify_internal_api_key)
):
    """
    Receive user corrections for parsed transactions.
    Implements Feedback Learning by updating the CorrectionStore dynamically.
    """
    logger.info(
        "FEEDBACK_LOOP user_id=%s transaction_id=%s corrections=%s reason=%s",
        feedback.user_id,
        feedback.transaction_id,
        feedback.correction_data,
        feedback.reason or "none"
    )
    
    # ── FEEDBACK LEARNING HOOK ────────────────────────────────────
    # If the user corrected the category, we add a rule to the CorrectionStore
    # We expect 'description' and 'category' in the correction_data for learning
    desc = feedback.correction_data.get("description")
    cat = feedback.correction_data.get("category")
    
    if desc and cat:
        CorrectionStore.add_correction(str(desc), str(cat))
        logger.info(f"Feedback learning activated: '{desc}' will now be '{cat}'")
    
    return {
        "status": "recorded", 
        "transaction_id": feedback.transaction_id,
        "message": "Feedback captured. System categorization rules updated."
    }
