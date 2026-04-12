import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

def adjust_plan(user_id: int, plan_id: int, adjustment_data: dict) -> dict:
    """
    Send a POST request to finance-service to adjust an existing financial plan.
    adjustment_data = {
        "monthly_saving": float,
        "deadline": str, # ISO date
        "status": str,
        "reasoning": str
    }
    """
    url = f"{settings.finance_service_url}/internal/plans/adjust/{user_id}/{plan_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=adjustment_data, headers=headers)
            response.raise_for_status()
            logger.info(f"Plan {plan_id} adjusted successfully for user {user_id}")
            return response.json()
    except Exception as e:
        logger.error(f"Error adjusting plan {plan_id} for user {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)}
