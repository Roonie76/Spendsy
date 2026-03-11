import os
import requests
import json
from typing import Dict, List, Any

FINANCE_SERVICE_URL = os.getenv("FINANCE_SERVICE_URL", "http://localhost:8002")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "internal-dev-key")

def call_finance_internal(endpoint: str, user_id: int, params: Dict = None):
    url = f"{FINANCE_SERVICE_URL}/internal/{endpoint}/{user_id}"
    headers = {"X-Internal-API-Key": INTERNAL_API_KEY}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        return response.json().get("data", {})
    except Exception as e:
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
