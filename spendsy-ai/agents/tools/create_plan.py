import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

def create_plan(user_id: int, plan_data: dict) -> dict:
    """
    Send a POST request to finance-service to create a new financial plan.
    plan_data = {
        "title": str,
        "source": str, # 'ai' or 'manual'
        "target_amount": float,
        "current_saved": float,
        "deadline": str, # ISO date
        "monthly_saving": float,
        "daily_saving": float,
        "confidence_score": float,
        "reasoning": str,
        "status": str
    }
    """
    url = f"{settings.finance_service_url}/internal/plans/create/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=plan_data, headers=headers)
            response.raise_for_status()
            logger.info(f"Plan created successfully for user {user_id}")
            return response.json()
    except Exception as e:
        logger.error(f"Error creating plan for user {user_id}: {str(e)}")
        return {"status": "error", "message": str(e)}
