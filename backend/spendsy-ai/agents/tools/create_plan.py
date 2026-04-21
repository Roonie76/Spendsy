import logging
import httpx
from config import settings

logger = logging.getLogger(__name__)

def create_plan(user_id: int, plan_data: dict) -> dict:
    """
    Send a POST request to finance-service to create a new financial plan.
    Handles mapping from LLM-provided camelCase to API snake_case.
    """
    url = f"{settings.finance_service_url}/internal/plans/create/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    # Map fields from LLM (camelCase) to Internal API (snake_case)
    mapped_data = {
        "title": plan_data.get("title", "New AI Plan"),
        "source": "ai",
        "target_amount": float(plan_data.get("target_amount", plan_data.get("targetAmount", 0))),
        "current_saved": float(plan_data.get("current_saved", plan_data.get("currentSaved", 0))),
        "deadline": plan_data.get("deadline", plan_data.get("deadline_iso", "2025-12-31T23:59:59Z")),
        "monthly_saving": float(plan_data.get("monthly_saving", plan_data.get("monthlySaving", 0))),
        "reasoning": plan_data.get("reasoning", ""),
        "status": plan_data.get("status", "on_track")
    }
    
    # Calculate daily saving if not provided (required by API)
    if "daily_saving" not in plan_data and "dailySaving" not in plan_data:
        mapped_data["daily_saving"] = mapped_data["monthly_saving"] / 30.0
    else:
        mapped_data["daily_saving"] = float(plan_data.get("daily_saving", plan_data.get("dailySaving", 0)))
        
    try:
        with httpx.Client(timeout=10.0) as client:
            logger.info(f"Sending mapped plan data to {url}: {mapped_data}")
            response = client.post(url, json=mapped_data, headers=headers)
            response.raise_for_status()
            logger.info(f"Plan created successfully for user {user_id}")
            return response.json()
    except Exception as e:
        logger.error(f"Error creating plan for user {user_id}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
             logger.error(f"Response body: {e.response.text}")
        return {"status": "error", "message": str(e)}
