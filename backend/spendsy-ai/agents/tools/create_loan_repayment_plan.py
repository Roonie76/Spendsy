import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

def create_loan_repayment_plan(user_id: int, plan_data: dict) -> dict:
    """
    Send a POST request to finance-service to create a new financial plan specifically for a loan.
    plan_data = {
        "loan_id": int,
        "title": str,
        "source": str, # usually 'ai'
        "target_amount": float, # Remaining balance
        "deadline": str, # Projected closure date
        "monthly_saving": float, # Extra EMI amount
        "reasoning": str,
        "status": str
    }
    """
    # Map to the standard internal plan creation endpoint which now handles loan_id
    url = f"{settings.finance_service_url}/internal/plans/create/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    # Ensure mandatory fields for the backend are present
    if "daily_saving" not in plan_data and "monthly_saving" in plan_data:
        plan_data["daily_saving"] = float(plan_data["monthly_saving"]) / 30
        
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=plan_data, headers=headers)
            response.raise_for_status()
            logger.info(f"Loan repayment plan created successfully for user {user_id}")
            return response.json()
    except Exception as e:
        logger.error(f"Error creating loan repayment plan for user {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)}
