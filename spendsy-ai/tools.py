import json
import logging
import httpx
from typing import Dict, List, Any
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from config import settings

logger = logging.getLogger(__name__)

def _is_retryable(e: Exception) -> bool:
    if isinstance(e, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code >= 500 or e.response.status_code == 429
    return False

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable),
)
def call_finance_internal(endpoint: str, user_id: int, params: Dict | None = None):
    url = f"{settings.finance_service_url}/internal/{endpoint}/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    with httpx.Client(timeout=10.0) as client:
        response = client.get(url, params=params, headers=headers)
        if response.status_code >= 500 or response.status_code == 429:
            response.raise_for_status()
        if not response.is_success:
            logger.error(f"Error calling finance service: {response.status_code} {response.text}")
            return None
            
        return response.json().get("data", {})

def get_summary(user_id: int) -> str:
    """Get a financial summary (income, expenses, balance) for a user."""
    data = call_finance_internal("summary", user_id)
    return json.dumps(data, indent=2) if data else "Error fetching summary."

def get_transactions(user_id: int, limit: int = 50) -> str:
    """Fetch the latest transactions for a user."""
    data = call_finance_internal("transactions", user_id, {"limit": limit})
    return json.dumps(data, indent=2) if data else "No transactions found."

def spending_insights(user_id: int) -> str:
    """Generate high-level spending insights."""
    transactions = call_finance_internal("transactions", user_id, {"limit": 1000})
    if not transactions:
        return "No transactions found to analyze."
        
    expenses = [t for t in transactions if t["type"] == "expense"]
    if not expenses:
        return "No expenses found to analyze."

    total_spend = sum(t["amount"] for t in expenses)
    avg_size = total_spend / len(expenses)
    
    cats = {}
    for t in expenses:
        c = t.get("category") or "Uncategorized"
        cats[c] = cats.get(c, 0) + t["amount"]
        
    largest_cat = max(cats.items(), key=lambda x: x[1])[0]
    
    insights = {
        "total_monthly_spend": total_spend,
        "average_transaction_size": round(avg_size, 2),
        "largest_category": largest_cat
    }
    return json.dumps(insights, indent=2)

def subscription_detection(user_id: int) -> str:
    """Identify potential recurring subscriptions."""
    transactions = call_finance_internal("transactions", user_id, {"limit": 1000})
    if not transactions: return "[]"
    
    keywords = ["netflix", "spotify", "gym", "amazon prime", "icloud", "youtube premium", "hulu", "disney"]
    found = []
    for t in transactions:
        title_lower = t["title"].lower()
        if any(k in title_lower for k in keywords):
            found.append(t)
    
    return json.dumps(found, indent=2)

def budget_recommendation(user_id: int) -> str:
    """Recommend a monthly budget."""
    summary = call_finance_internal("summary", user_id)
    if not summary: return "Advice: Monitor your spending habits."
    
    income = summary.get("income", 0)
    expense = summary.get("expense", 0)
    
    suggested = round(income * 0.7, 2) if income > 0 else round(expense * 0.9, 2)
    
    return json.dumps({
        "current_monthly_income": income,
        "current_monthly_expense": expense,
        "suggested_budget": suggested,
        "advice": "50/30/20 rule: 50% Needs, 30% Wants, 20% Savings."
    }, indent=2)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable),
)
def create_plan(user_id: int, title: str, description: str, target_amount: float = 0, target_date: str | None = None) -> str:
    """Invoked by TORA to create a new financial goal/plan."""
    if not target_date:
        from datetime import datetime, timedelta
        target_date = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
        
    url = f"{settings.finance_service_url}/internal/goals/{user_id}"
    payload = {
        "title": title, 
        "description": description, 
        "target_amount": target_amount, 
        "current_amount": 0, 
        "target_date": target_date, 
        "category": "General", 
        "is_completed": False
    }
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, json=payload, headers=headers)
        if response.status_code >= 500 or response.status_code == 429:
            response.raise_for_status()
        if response.is_success:
            return json.dumps({"status": "success", "message": "Plan created successfully"})
        else:
            return json.dumps({"status": "error", "message": f"Server error: {response.status_code}"})

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable),
)
def delete_plan(user_id: int, plan_id: str) -> str:
    """Invoked by TORA to delete an existing financial goal/plan."""
    url = f"{settings.finance_service_url}/internal/goals/{user_id}/{plan_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    with httpx.Client(timeout=10.0) as client:
        response = client.delete(url, headers=headers)
        if response.status_code >= 500 or response.status_code == 429:
            response.raise_for_status()
        if response.is_success:
            return json.dumps({"status": "success", "message": f"Plan {plan_id} deleted successfully"})
        else:
            return json.dumps({"status": "error", "message": f"Server error: {response.status_code}"})
