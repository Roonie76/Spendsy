import json
import logging
import copy
import re
from typing import Dict, Any, List
import urllib.request
import urllib.error
import urllib.parse
import os
import sys

# Ensure parent directory is in path for tools import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
        "goals": context.get("goals", []),
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
        
    # Clean goals
    for goal in clean_summary.get("goals", []):
        goal.pop("id", None)
        goal.pop("user_id", None)
        
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


def _clean_json_response(raw_response: str) -> str:
    """Remove markdown code blocks and whitespace from AI response."""
    # Remove ```json ... ``` or ``` ... ```
    clean = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", raw_response, flags=re.DOTALL)
    return clean.strip()


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
        
        # Clean and parse the structured JSON response
        try:
            clean_response = _clean_json_response(raw_response)
            structured_advice = json.loads(clean_response)
            
            # Execute tools if requested
            if "tool_calls" in structured_advice and isinstance(structured_advice["tool_calls"], list):
                from tools import create_plan, delete_plan
                for tool in structured_advice["tool_calls"]:
                    try:
                        name = tool.get("name")
                        params = tool.get("parameters", {})
                        if name == "create_plan":
                            logger.info(f"TORA executing tool: create_plan for user {user_id}")
                            create_plan(
                                user_id, 
                                str(params.get("title", "Financial Plan")), 
                                str(params.get("description", "")),
                                float(params.get("target_amount", 0)),
                                params.get("target_date")
                            )
                        elif name == "delete_plan":
                            plan_id = params.get("plan_id")
                            if plan_id:
                                logger.info(f"TORA executing tool: delete_plan {plan_id} for user {user_id}")
                                delete_plan(user_id, str(plan_id))
                        else:
                            logger.warning(f"Unknown tool requested by TORA: {name}")
                    except Exception as e:
                        logger.error(f"Error executing TORA tool {tool}: {e}")
            
            # Return either the 'answer' part or the whole thing if not nested
            final_output = structured_advice.get("answer", structured_advice)
            
            # Ensure required keys exist in the conversational part
            required_keys = ["Financial Overview", "Current Position", "Recommended Strategy", "Expected Outcome"]
            for key in required_keys:
                if key not in final_output:
                    final_output[key] = "N/A"
                    
            return final_output
            
        except json.JSONDecodeError:
            logger.error(f"AI response was not valid JSON: {raw_response}")
            return {
                "Financial Overview": "I encountered an error while processing your request. Could you please try again?",
                "Current Position": "N/A",
                "Recommended Strategy": "N/A",
                "Expected Outcome": "N/A",
                "error": "AI returned malformed structured data."
            }
            
    except Exception as e:
        logger.error(f"TORA execution failed: {e}")
        return {
            "Financial Overview": f"I'm sorry, I encountered a technical difficulty: {str(e)}",
            "Current Position": "N/A",
            "Recommended Strategy": "N/A",
            "Expected Outcome": "N/A"
        }


def _save_conversation(user_id: int, role: str, content: str, structured: Dict[str, Any] | None = None) -> None:
    """
    Persist a single conversation turn to the finance-service internal API.
    The ToraConversation table is owned by finance-service for co-location with
    user data, but written to via the internal API key.
    """
    url = f"{settings.finance_service_url}/internal/tora-conversation/{user_id}"
    payload = {
        "role": role,
        "content": content,
    }
    if structured:
        payload["financial_overview"] = structured.get("Financial Overview", "")
        payload["current_position"] = structured.get("Current Position", "")
        payload["recommended_strategy"] = structured.get("Recommended Strategy", "")
        payload["expected_outcome"] = structured.get("Expected Outcome", "")

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Internal-API-Key": settings.internal_api_key,
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3):
            pass
    except Exception as e:
        logger.warning(f"Could not save conversation turn: {e}")


def _load_recent_conversation(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Load the last N conversation turns for a user.
    Returns a list of dicts with 'role' and 'content' keys for prompt injection.
    """
    data = call_finance_internal("tora-conversation", user_id, {"limit": limit})
    if not data or not isinstance(data, list):
        return []
    history = []
    for msg in data:
        history.append({
            "role": msg.get("role", "user"),
            "content": msg.get("content", ""),
        })
    return history


def handle_user_question(user_id: int, question: str) -> Dict[str, Any]:
    """
    Main entry point for the TORA agent endpoint.
    1. Detects message intent (greeting, finance, or other).
    2. Routes to local responses or AI workflow.
    3. Persists conversation history for memory across sessions.
    """

    # 1. Intent Detection
    intent = detect_intent(question)

    if intent == "greeting":
        logger.info(f"Greeting detected: {question}")
        response = json.loads(get_greeting_response())
        _save_conversation(user_id, "user", question)
        _save_conversation(user_id, "assistant", response.get("Financial Overview", ""), response)
        return response

    if intent == "non_finance_query":
        logger.info(f"Non-financial query detected: {question}")
        response = json.loads(get_fallback_response())
        _save_conversation(user_id, "user", question)
        _save_conversation(user_id, "assistant", response.get("Financial Overview", ""), response)
        return response

    # 2. Proceed with financial intelligence lifecycle for 'finance_query'
    # Save the user turn first
    _save_conversation(user_id, "user", question)

    try:
        strategy_json = generate_financial_strategy(user_id, question)
        # Persist the assistant response
        _save_conversation(user_id, "assistant", strategy_json.get("Financial Overview", ""), strategy_json)
        return strategy_json
    except Exception as e:
        logger.error(f"TORA execution failed: {str(e)}")
        raise
