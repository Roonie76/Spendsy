import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

def adjust_plan(user_id: int, plan_id: int, adjustment_data: dict) -> dict:
    """
    Send a POST request to finance-service to adjust an existing financial plan.
    Handles mapping from LLM-provided camelCase to API snake_case.
    """
    url = f"{settings.finance_service_url}/internal/plans/adjust/{user_id}/{plan_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    # Map fields from LLM (camelCase) to Internal API (snake_case)
    mapped_data = {}
    if "monthly_saving" in adjustment_data or "monthlySaving" in adjustment_data:
        mapped_data["monthly_saving"] = float(adjustment_data.get("monthly_saving", adjustment_data.get("monthlySaving")))
    
    if "deadline" in adjustment_data:
        mapped_data["deadline"] = adjustment_data["deadline"]
        
    if "status" in adjustment_data:
        mapped_data["status"] = adjustment_data["status"]
        
    if "reasoning" in adjustment_data:
        mapped_data["reasoning"] = adjustment_data["reasoning"]
        
    if "title" in adjustment_data:
        mapped_data["title"] = adjustment_data["title"]
        
    try:
        with httpx.Client(timeout=10.0) as client:
            logger.info(f"Sending mapped adjustment data to {url}: {mapped_data}")
            response = client.post(url, json=mapped_data, headers=headers)
            response.raise_for_status()
            logger.info(f"Plan {plan_id} adjusted successfully for user {user_id}")
            return response.json()
    except Exception as e:
        logger.error(f"Error adjusting plan {plan_id} for user {user_id}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Response body: {e.response.text}")
        return {"status": "error", "message": str(e)}
