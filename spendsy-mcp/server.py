import asyncio
import json
import mimetypes
import os
import hashlib
import uuid
import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential
from mcp.server.fastmcp import FastMCP

from config import settings

# Initialize FastMCP server
mcp = FastMCP("Spendsy Financial Assistant")

def _is_retryable(e: Exception) -> bool:
    if isinstance(e, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code >= 500 or e.response.status_code == 429
    return False

# Helper to call finance-service internal APIs
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable),
)
def call_finance_internal(endpoint: str, user_id: int, params: Dict | None = None):
    url = f"{settings.finance_service_url.rstrip('/')}/internal/{endpoint}/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    with httpx.Client(timeout=10.0) as client:
        response = client.get(url, params=params, headers=headers)
        if response.status_code >= 500 or response.status_code == 429:
            response.raise_for_status()
        return response.json().get("data", {})


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable),
)
def _post_file(url: str, file_path: str) -> dict[str, Any]:
    filename = os.path.basename(file_path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    
    with open(file_path, "rb") as f:
        files = {"file": (filename, f, content_type)}
        headers = {"X-Internal-API-Key": settings.internal_api_key}
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, files=files, headers=headers)
            if response.status_code >= 500 or response.status_code == 429:
                response.raise_for_status()
            return response.json()

# --- SECTION 3: Core MCP Tools ---

@mcp.tool()
def get_transactions(user_id: int, limit: int = 20) -> str:
    """Fetch the latest transactions for a user."""
    try:
        data = call_finance_internal("transactions", user_id, {"limit": limit})
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error fetching transactions: {str(e)}"

@mcp.tool()
def get_summary(user_id: int) -> str:
    """Get a financial summary (income, expenses, balance) for a user."""
    try:
        data = call_finance_internal("summary", user_id)
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error fetching summary: {str(e)}"

@mcp.tool()
def monthly_spend(user_id: int, month: str) -> str:
    """
    Calculate total spend for a specific month.
    Input format: YYYY-MM
    """
    try:
        transactions = call_finance_internal("transactions", user_id, {"limit": 1000})
        total = sum(
            t["amount"] for t in transactions 
            if t["type"] == "expense" and t["date"].startswith(month)
        )
        return json.dumps({"month": month, "total_spend": total}, indent=2)
    except Exception as e:
        return f"Error calculating monthly spend: {str(e)}"

@mcp.tool()
def spending_by_category(user_id: int) -> str:
    """Breakdown total spending by category."""
    try:
        transactions = call_finance_internal("transactions", user_id, {"limit": 1000})
        categories = {}
        for t in transactions:
            if t["type"] == "expense":
                cat = t.get("category") or "Uncategorized"
                categories[cat] = categories.get(cat, 0) + t["amount"]
        return json.dumps(categories, indent=2)
    except Exception as e:
        return f"Error calculating spending by category: {str(e)}"

@mcp.tool()
def top_merchants(user_id: int, limit: int = 5) -> str:
    """Identify top merchants/locations by spend."""
    try:
        transactions = call_finance_internal("transactions", user_id, {"limit": 1000})
        merchants = {}
        for t in transactions:
            if t["type"] == "expense":
                title = t.get("title") or "Unknown"
                merchants[title] = merchants.get(title, 0) + t["amount"]
        
        sorted_merchants = sorted(merchants.items(), key=lambda x: x[1], reverse=True)
        return json.dumps(dict(sorted_merchants[:limit]), indent=2)
    except Exception as e:
        return f"Error identifying top merchants: {str(e)}"

@mcp.tool()
def spending_insights(user_id: int) -> str:
    """Generate high-level spending insights."""
    try:
        transactions = call_finance_internal("transactions", user_id, {"limit": 1000})
        if not transactions:
            return "No transactions found to analyze."
            
        expenses = [t for t in transactions if t["type"] == "expense"]
        if not expenses:
            return "No expenses found to analyze."

        total_spend = sum(t["amount"] for t in expenses)
        avg_size = total_spend / len(expenses)
        
        cats = {}
        merchants = {}
        for t in expenses:
            c = t.get("category") or "Uncategorized"
            m = t.get("title") or "Unknown"
            cats[c] = cats.get(c, 0) + t["amount"]
            merchants[m] = merchants.get(m, 0) + t["amount"]
            
        largest_cat = max(cats.items(), key=lambda x: x[1])[0]
        largest_merchant = max(merchants.items(), key=lambda x: x[1])[0]
        
        insights = {
            "total_monthly_spend": total_spend,
            "average_transaction_size": round(avg_size, 2),
            "largest_category": largest_cat,
            "largest_merchant": largest_merchant
        }
        return json.dumps(insights, indent=2)
    except Exception as e:
        return f"Error generating insights: {str(e)}"

# --- SECTION 4: Transaction Fingerprinting ---

@mcp.tool()
def detect_duplicate_transactions(user_id: int) -> str:
    """Identify potential duplicate transactions using fingerprinting."""
    try:
        transactions = call_finance_internal("transactions", user_id, {"limit": 1000})
        fingerprints = {}
        duplicates = []
        
        for t in transactions:
            # sha256(user_id + date + amount + normalized_title)
            raw = f"{user_id}|{t['date']}|{t['amount']}|{t['title'].lower().strip()}"
            fp = hashlib.sha256(raw.encode()).hexdigest()
            
            if fp in fingerprints:
                duplicates.append({
                    "original": fingerprints[fp],
                    "duplicate": t
                })
            else:
                fingerprints[fp] = t
                
        return json.dumps({"duplicate_count": len(duplicates), "duplicates": duplicates}, indent=2)
    except Exception as e:
        return f"Error detecting duplicates: {str(e)}"

# --- SECTION 5: File Parsing ---

@mcp.tool()
def parse_statement(file_path: str) -> str:
    """Parse a financial statement file through the parser service."""
    try:
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
            
        url = f"{settings.parser_service_url}/parser/parse"
        return json.dumps(_post_file(url, file_path), indent=2)
    except (HTTPError, URLError, json.JSONDecodeError, OSError) as e:
        return f"Error parsing statement: {str(e)}"

# --- SECTION 6: Database Query Tool ---

@mcp.tool()
def query_spending_data(user_id: int, query_type: str) -> str:
    """
    Run a predefined safe query on spending data.
    Supported query_types: 'monthly_category_totals', 'merchant_statistics', 'income_expense_ratio'
    """
    try:
        transactions = call_finance_internal("transactions", user_id, {"limit": 1000})
        
        if query_type == "monthly_category_totals":
            result = {}
            for t in transactions:
                if t["type"] == "expense":
                    month = t["date"][:7]
                    cat = t.get("category") or "Uncategorized"
                    result[month] = result.get(month, {})
                    result[month][cat] = result[month].get(cat, 0) + t["amount"]
            return json.dumps(result, indent=2)
            
        elif query_type == "merchant_statistics":
            stats = {}
            for t in transactions:
                if t["type"] == "expense":
                    m = t["title"]
                    if m not in stats:
                        stats[m] = {"count": 0, "total": 0.0, "avg": 0.0}
                    stats[m]["count"] += 1
                    stats[m]["total"] += t["amount"]
                    stats[m]["avg"] = stats[m]["total"] / stats[m]["count"]
            return json.dumps(stats, indent=2)
            
        elif query_type == "income_expense_ratio":
            summary = call_finance_internal("summary", user_id)
            inc = summary.get("income", 0)
            exp = summary.get("expense", 0)
            ratio = inc / exp if exp > 0 else inc
            return json.dumps({"income": inc, "expense": exp, "ratio": ratio}, indent=2)
            
        else:
            return f"Unsupported query type: {query_type}"
    except Exception as e:
        return f"Error running query: {str(e)}"

# --- SECTION 7: Financial Advisor Tools ---

@mcp.tool()
def spending_trend_analysis(user_id: int) -> str:
    """Analyze spending trends over time."""
    try:
        transactions = call_finance_internal("transactions", user_id, {"limit": 1000})
        monthly = {}
        for t in transactions:
            if t["type"] == "expense":
                m = t["date"][:7]
                monthly[m] = monthly.get(m, 0) + t["amount"]
                
        sorted_months = sorted(monthly.items())
        trends = []
        for i in range(1, len(sorted_months)):
            prev_m, prev_v = sorted_months[i-1]
            curr_m, curr_v = sorted_months[i]
            growth = ((curr_v - prev_v) / prev_v) * 100 if prev_v > 0 else 0
            trends.append({
                "period": f"{prev_m} to {curr_m}",
                "previous": prev_v,
                "current": curr_v,
                "growth_percentage": round(growth, 2)
            })
            
        return json.dumps({"monthly_spending": monthly, "trends": trends}, indent=2)
    except Exception as e:
        return f"Error analyzing trends: {str(e)}"

@mcp.tool()
def budget_recommendation(user_id: int) -> str:
    """Recommend a monthly budget based on historical spending."""
    try:
        summary = call_finance_internal("summary", user_id)
        income = summary.get("income", 0)
        expense = summary.get("expense", 0)
        
        # Simple recommendation: 50/30/20 rule or historical - 10%
        suggested = round(income * 0.7, 2) if income > 0 else round(expense * 0.9, 2)
        
        return json.dumps({
            "current_income": income,
            "current_expense": expense,
            "suggested_monthly_budget": suggested,
            "advice": "Consider the 50/30/20 rule: 50% for needs, 30% for wants, and 20% for savings/debt."
        }, indent=2)
    except Exception as e:
        return f"Error generating budget recommendation: {str(e)}"

@mcp.tool()
def subscription_detection(user_id: int) -> str:
    """Identify potential recurring subscriptions."""
    try:
        transactions = call_finance_internal("transactions", user_id, {"limit": 1000})
        # Basic keyword matching for demo
        keywords = ["netflix", "spotify", "gym", "amazon prime", "icloud", "youtube premium", "hulu", "disney"]
        found = []
        for t in transactions:
            title_lower = t["title"].lower()
            if any(k in title_lower for k in keywords):
                found.append(t)
        
        return json.dumps({"subscriptions_found": found}, indent=2)
    except Exception as e:
        return f"Error detecting subscriptions: {str(e)}"

# --- SECTION 8: Total Financial Liberty Tools ---

@mcp.tool()
def get_full_financial_context(user_id: int) -> str:
    """
    Exhaustive financial profile of the user. 
    Includes: Income, Budgets, Assets, Liabilities, Net Worth, Tax Profile, ITR data, and recent transactions.
    Use this for complex planning (buying a house, early loan closure, retirement planning).
    """
    try:
        data = call_finance_internal("finance-context", user_id)
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"Error fetching full context: {str(e)}"

@mcp.tool()
def simulate_loan_closure(user_id: int, current_balance: float, interest_rate: float, additional_monthly_payment: float) -> str:
    """
    Simulate the impact of paying more towards a loan.
    Input: balance, annual interest rate (%), extra monthly payment.
    """
    monthly_rate = (interest_rate / 100) / 12
    # Simple simulation to show time/interest saved
    # This is a basic amortized calculation for illustrative planning
    
    current_context = call_finance_internal("summary", user_id)
    balance = current_context.get("balance", 0)
    
    if additional_monthly_payment > balance:
        return f"Warning: Your current monthly balance ({balance}) is less than the proposed extra payment ({additional_monthly_payment})."

    # Simplified summary for the AI to reason with
    return json.dumps({
        "status": "Ready for planning",
        "current_user_monthly_balance": balance,
        "simulation_parameters": {
            "loan_balance": current_balance,
            "interest_rate": interest_rate,
            "extra_payment": additional_monthly_payment
        },
        "approach": "AI should now calculate the months saved and interest avoided based on these parameters."
    }, indent=2)

@mcp.tool()
def simulate_house_purchase(user_id: int, house_price: float, down_payment: float, annual_interest_rate: float, tenure_years: int) -> str:
    """
    Evaluate the feasibility of buying a house based on user context.
    """
    try:
        context = call_finance_internal("finance-context", user_id)
        wealth = context.get("wealth", {})
        profile = context.get("profile", {})
        
        liquid_assets = wealth.get("assets", 0)
        monthly_income = profile.get("monthlyIncome", 0)
        
        loan_amount = house_price - down_payment
        monthly_rate = (annual_interest_rate / 100) / 12
        num_payments = tenure_years * 12
        
        # EMI = [P x R x (1+R)^N]/[(1+R)^N-1]
        emi = (loan_amount * monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
        
        feasibility = "feasible" if emi < (monthly_income * 0.4) and down_payment <= liquid_assets else "strained"
        
        return json.dumps({
            "house_price": house_price,
            "down_payment": down_payment,
            "loan_required": loan_amount,
            "estimated_emi": round(emi, 2),
            "available_assets": liquid_assets,
            "monthly_income": monthly_income,
            "feasibility_score": feasibility,
            "recommendation": "Feasible if EMI < 40% of income and assets cover down payment."
        }, indent=2)
    except Exception as e:
        return f"Error simulating house purchase: {str(e)}"

if __name__ == "__main__":
    mcp.run()
