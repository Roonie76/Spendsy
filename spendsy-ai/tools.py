
import json
from typing import Dict, List, Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

from config import settings

def call_finance_internal(endpoint: str, user_id: int, params: Dict | None = None):
    url = f"{settings.finance_service_url}/internal/{endpoint}/{user_id}"
    if params:
        url = f"{url}?{parse.urlencode(params)}"
    req = request.Request(url, headers={"X-Internal-API-Key": settings.internal_api_key}, method="GET")
    try:
        with request.urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload.get("data", {})
    except (HTTPError, URLError, json.JSONDecodeError) as e:
        print(f"Error calling finance service: {e}")
        return None

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

def create_plan(user_id: int, title: str, description: str, target_amount: float = 0, target_date: str | None = None) -> str:
    """Invoked by TORA to create a new financial goal/plan."""
    if not target_date:
        from datetime import datetime, timedelta
        target_date = (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z"
        
    url = f"{settings.finance_service_url}/internal/goals/{user_id}"
    payload = json.dumps({
        "title": title, 
        "description": description, 
        "target_amount": target_amount, 
        "current_amount": 0, 
        "target_date": target_date, 
        "category": "General", 
        "is_completed": False
    }).encode("utf-8")
    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "X-Internal-API-Key": settings.internal_api_key},
        method="POST"
    )
    try:
        with request.urlopen(req, timeout=5) as response:
            return json.dumps({"status": "success", "message": "Plan created successfully"})
    except Exception as e:
        print(f"Error calling create_plan: {e}")
        return json.dumps({"status": "error", "message": str(e)})

def delete_plan(user_id: int, plan_id: str) -> str:
    """Invoked by TORA to delete an existing financial goal/plan."""
    url = f"{settings.finance_service_url}/internal/goals/{user_id}/{plan_id}"
    req = request.Request(
        url,
        headers={"X-Internal-API-Key": settings.internal_api_key},
        method="DELETE"
    )
    try:
        with request.urlopen(req, timeout=5) as response:
            return json.dumps({"status": "success", "message": f"Plan {plan_id} deleted successfully"})
    except Exception as e:
        print(f"Error calling delete_plan: {e}")
        return json.dumps({"status": "error", "message": str(e)})
