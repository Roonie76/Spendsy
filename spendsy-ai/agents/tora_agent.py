import json
import json
import logging
import copy
from typing import Dict, Any, List
import urllib.request
import urllib.error
import urllib.parse
import os

from config import settings
from .tora_personality import TORA_SYSTEM_PROMPT, detect_intent, get_greeting_response, get_fallback_response

logger = logging.getLogger(__name__)

# Try to import internal tools for API calls
try:
    from tools import call_finance_internal
except ImportError:
    # Handle the case where TORA is run standalone
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools import call_finance_internal as call_finance_internal_fallback # Renamed to avoid conflict if tools is not found
    call_finance_internal = call_finance_internal_fallback # Assign fallback to original name

# Try to import httpx or requests for OpenAI API calls
try:
    import httpx
    has_httpx = True
except ImportError:
    has_httpx = False


def fetch_financial_summary(user_id: int) -> Dict[str, Any]:
    """
    Fetch a complete financial snapshot of the user from internal services.
    """
    logger.info(f"Fetching financial summary for user {user_id}")
    context = call_finance_internal("finance-context", user_id)
    if not context:
        return {}

    # Extract required fields mapping to the expected structure
    summary = context.get("summary", {})
    profile = context.get("profile", {})
    
    return {
        "monthly_income": profile.get("monthlyIncome", 0) or summary.get("income", 0),
        "monthly_budget": profile.get("monthlyBudget", 0),
        "monthly_expenses": summary.get("expense", 0),
        "account_balance": summary.get("balance", 0),
        "monthly_surplus": (profile.get("monthlyIncome", 0) or summary.get("income", 0)) - summary.get("expense", 0),
        "loans": context.get("loans", []),
        "credit_cards": context.get("credit_cards", []),
        "recent_transactions": context.get("recent_transactions", [])
    }


def run_financial_simulations(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run mathematical simulations (e.g., early EMI closure savings)
    before handing off to the AI.
    """
    simulations = {"loan_optimizations": []}
    
    loans = summary.get("loans", [])
    for loan in loans:
        # Simple simulation: What if they put their entire current surplus into this loan?
        surplus = float(summary.get("monthly_surplus", 0))
        principal = float(loan.get("remaining_balance", 0))
        
        # We need an interest rate (default to 10% if not provided by the finance-context endpoint yet)
        rate = float(loan.get("interest_rate", 10.5)) / 100.0 / 12.0
        emi = float(loan.get("emi_amount", loan.get("principal_amount", principal) * 0.05)) # Rough guess if EMI missing
        
        # Don't simulate if it's already paid off or bad data
        if principal <= 0 or surplus <= 0:
            continue
            
        # Very rough estimation of months saved by paying an extra 'surplus' amount
        # Standard amortization math approximation for AI context
        try:
            standard_months = principal / emi if emi > 0 else 0
            accelerated_months = principal / (emi + surplus) if (emi + surplus) > 0 else 0
            months_saved = max(0, int(standard_months - accelerated_months))
            
            simulations["loan_optimizations"].append({
                "loan_id_ref": str(loan.get("id")),
                "loan_type": loan.get("loan_type", "unknown"),
                "extra_payment_scenario": float(surplus),
                "estimated_months_saved": months_saved,
                "viability": "high" if months_saved > 6 else "moderate"
            })
        except Exception as e:
            logger.warning(f"Simulation math failed for loan {loan.get('id')}: {e}")
            
    return simulations


def sanitize_financial_data(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Strictly remove PII, account numbers, and exact identifiers before sending to OpenAI.
    """
    clean_summary = copy.deepcopy(summary)
    
    # Clean loans
    for loan in clean_summary.get("loans", []):
        loan.pop("id", None)
        loan.pop("user_id", None)
        loan.pop("bank_name", None)
        loan.pop("account_number", None)
        
    # Clean credit cards
    for card in clean_summary.get("credit_cards", []):
        card.pop("id", None)
        card.pop("name", None) # Could contain bank names e.g. "HDFC Millenia"
        card.pop("last_four_digits", None)
        card.pop("card_holder_name", None)
        
    # Clean transactions (Only keep categories and amounts, drop titles/descriptions)
    clean_txs = []
    for tx in clean_summary.get("recent_transactions", []):
        clean_txs.append({
            "amount": float(tx.get("amount", 0)),
            "type": tx.get("type", "unknown"),
            "category": tx.get("category", "unknown"),
            "is_recurring": tx.get("is_recurring", False)
        })
    clean_summary["recent_transactions"] = clean_txs
    
    return clean_summary


def build_ai_context(summary: Dict[str, Any], simulations: Dict[str, Any], question: str) -> str:
    """
    Construct the final system prompt string containing the financial state,
    the simulation results, and strict output instructions.
    """
    
    prompt = f"{TORA_SYSTEM_PROMPT}\n\n"
    prompt += "FINANCIAL SUMMARY (SANITIZED):\n"
    prompt += json.dumps(summary, indent=2) + "\n\n"
    
    if simulations:
        prompt += "FINANCIAL SIMULATIONS:\n"
        prompt += json.dumps(simulations, indent=2) + "\n\n"
        
    prompt += f"USER QUESTION: {question}\n\n"
    prompt += "INSTRUCTIONS:\n"
    prompt += "1. Read the user question carefully.\n"
    prompt += "2. Analyze the sanitized financial summary and any provided simulations.\n"
    prompt += "3. Provide a response in valid JSON format matching the structure defined in your primary instructions."
    
    return prompt


def call_ai_api(context: str) -> str:
    """
    Execute the HTTP call to the Google Gemini API using gemini-1.5-flash-lite.
    """
    api_key = settings.google_api_key or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY environment variable is not set")
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    
    # Adapt the context/prompt for Gemini
    # Gemini 1.5 prefers a clear instruction to return JSON
    effective_prompt = f"{context}\n\nIMPORTANT: Return ONLY valid JSON. No markdown backticks, no preamble."
    
    payload = {
        "contents": [{"parts": [{"text": effective_prompt}]}],
        "generationConfig": {
            "temperature": 0.2
        }
    }
    
    # Use httpx if available (FastAPI standard), otherwise fallback to urllib
    if has_httpx:
        import httpx
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                raise RuntimeError(f"Gemini API Error: {response.text}")
            
            data = response.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError):
                logger.error(f"Unexpected Gemini response structure: {data}")
                raise RuntimeError("Gemini API returned an unexpected response structure")
    else:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'), 
            headers=headers, 
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30.0) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise RuntimeError(f"Gemini API Error ({e.code}): {error_body}")
        except Exception as e:
            raise RuntimeError(f"Request failed: {str(e)}")


def generate_financial_strategy(user_id: int, question: str) -> Dict[str, Any]:
    """
    The orchestrator function executing the full Agent Workflow.
    """
    # 1. Fetch
    raw_summary = fetch_financial_summary(user_id)
    if not raw_summary:
        return {"error": "Could not fetch user financial summary."}
        
    # 2. Simulate
    simulations = run_financial_simulations(raw_summary)
    
    # 3. Sanitize
    clean_summary = sanitize_financial_data(raw_summary)
    
    # 4. Contextualize
    prompt = build_ai_context(clean_summary, simulations, question)
    
    # 5. Execute
    try:
        raw_response = call_ai_api(prompt)
        
        # Parse the structured JSON response
        try:
            structured_advice = json.loads(raw_response)
            
            # Flatten if AI nested it inside an 'answer' key
            if "answer" in structured_advice and isinstance(structured_advice["answer"], dict):
                structured_advice = structured_advice["answer"]
            
            # Ensure required keys exist
            required_keys = ["Financial Overview", "Current Position", "Recommended Strategy", "Expected Outcome"]
            for key in required_keys:
                if key not in structured_advice:
                    structured_advice[key] = "Not provided by AI."
                    
            return structured_advice
            
        except json.JSONDecodeError:
            logger.error(f"AI response was not valid JSON: {raw_response}")
            return {"error": "AI returned malformed structured data.", "raw_response": raw_response}
            
    except Exception as e:
        logger.error(f"TORA execution failed: {e}")
        return {"error": f"Failed to generate strategy: {str(e)}"}


def handle_user_question(user_id: int, question: str) -> Dict[str, Any]:
    """
    Main entry point for the TORA agent endpoint.
    1. Detects message intent (greeting, finance, or other).
    2. Routes to local responses or AI workflow.
    """
    
    # 1. Intent Detection
    intent = detect_intent(question)
    
    if intent == "greeting":
        logger.info(f"Greeting detected: {question}")
        return json.loads(get_greeting_response())
        
    if intent == "non_finance_query":
        logger.info(f"Non-financial query detected: {question}")
        return json.loads(get_fallback_response())

    # 2. Proceed with financial intelligence lifecycle for 'finance_query'
    try:
        strategy_json = generate_financial_strategy(user_id, question)
        return strategy_json
    except Exception as e:
        logger.error(f"TORA execution failed: {str(e)}")
        raise
