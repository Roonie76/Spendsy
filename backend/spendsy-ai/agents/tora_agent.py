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
from tiering import TieringConfig
from memory import (
    load_user_conversation_history,
    inject_memory_into_system_prompt,
    get_tier_memory_limit,
    format_memory_stats
)
from .tora_personality import TORA_SYSTEM_PROMPT, detect_intent, get_greeting_response, get_fallback_response, get_capability_response, get_small_talk_response
from .llm_router import call_llm
from .tools.tool_registry import get_tool_registry
from mcp_connector import fetch_context_via_mcp

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


async def fetch_financial_summary(user_id: int) -> Dict[str, Any]:
    """
    Fetch a complete financial snapshot of the user via the MCP data pipeline.
    """
    logger.info(f"Fetching financial summary for user {user_id} via MCP")
    context = await fetch_context_via_mcp(user_id)
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
        "plans": context.get("plans", []),
        "recent_transactions": context.get("recent_transactions", [])
    }


def run_financial_simulations(summary: Dict[str, Any], user_tier: str = "free") -> Dict[str, Any]:
    """
    Run mathematical simulations based on user tier.
    Free tier: Basic savings rate analysis only
    Pro tier: Loan optimization + tax comparison
    Enterprise: All simulations including portfolio optimization
    """
    simulations = {}
    available_sims = TieringConfig.get_simulations(user_tier)
    
    # Basic savings rate (available to all tiers)
    if "basic_savings_rate" in available_sims:
        simulations["basic_savings_rate_analysis"] = {
            "monthly_income": float(summary.get("monthly_income", 0)),
            "monthly_expenses": float(summary.get("monthly_expenses", 0)),
            "monthly_surplus": float(summary.get("monthly_surplus", 0)),
            "savings_rate_pct": round(
                (float(summary.get("monthly_surplus", 0)) / float(summary.get("monthly_income", 1))) * 100,
                2
            ) if float(summary.get("monthly_income", 0)) > 0 else 0
        }
    
    # Loan optimizations (Pro tier and above)
    if "loan_optimization" in available_sims:
        simulations["loan_optimizations"] = []
        loans = summary.get("loans", [])
        for loan in loans:
            surplus = float(summary.get("monthly_surplus", 0))
            principal = float(loan.get("remaining_balance", 0))
            rate = float(loan.get("interest_rate", 10.5)) / 100.0 / 12.0
            emi = float(loan.get("emi_amount", loan.get("principal_amount", principal) * 0.05))
            
            if principal <= 0 or surplus <= 0:
                continue
                
            try:
                standard_months = principal / emi if emi > 0 else 0
                accelerated_months = principal / (emi + surplus) if (emi + surplus) > 0 else 0
                months_saved = max(0, int(standard_months - accelerated_months))
                
                simulations["loan_optimizations"].append({
                    "loan_type": loan.get("loan_type", "unknown"),
                    "extra_payment_scenario": float(surplus),
                    "estimated_months_saved": months_saved,
                    "viability": "high" if months_saved > 6 else "moderate"
                })
            except Exception as e:
                logger.warning(f"Simulation math failed: {e}")
    
    # Tax regime comparison (Pro tier and above)
    if "tax_regime_comparison" in available_sims:
        simulations["tax_regime_context"] = {
            "message": "Tax regime comparison available",
            "requires_full_profile": True
        }
    
    # Subscription detection (Pro tier and above)
    if "subscription_detection" in available_sims:
        simulations["recurring_transactions"] = {
            "count": len([t for t in summary.get("recent_transactions", []) if t.get("is_recurring")]),
            "analysis_available": True
        }
    
    return simulations


def sanitize_financial_data(summary: Dict[str, Any], user_tier: str = "free") -> Dict[str, Any]:
    """
    Sanitize financial data based on user tier.
    - Free tier: Strict PII removal
    - Pro tier: Limited context exposure for better categorization
    - Enterprise: High-context mode with necessary identifiers
    """
    clean_summary = copy.deepcopy(summary)
    expose_bank_names = TieringConfig.should_expose_pii(user_tier, "bank_names")
    expose_card_details = TieringConfig.should_expose_pii(user_tier, "card_details")
    expose_transaction_titles = TieringConfig.should_expose_pii(user_tier, "transaction_titles")
    
    # Clean loans
    for loan in clean_summary.get("loans", []):
        loan.pop("id", None)
        loan.pop("user_id", None)
        if not expose_bank_names:
            loan.pop("bank_name", None)
        loan.pop("account_number", None)
        
    # Clean credit cards
    for card in clean_summary.get("credit_cards", []):
        card.pop("id", None)
        if not expose_card_details:
            card.pop("name", None)  # Could contain bank names e.g. "HDFC Millenia"
        card.pop("last_four_digits", None)
        card.pop("card_holder_name", None)
        
    # Clean goals
    for goal in clean_summary.get("goals", []):
        goal.pop("id", None)
        goal.pop("user_id", None)
        
    # Clean transactions (handling based on tier)
    clean_txs = []
    for tx in clean_summary.get("recent_transactions", []):
        clean_tx = {
            "amount": float(tx.get("amount", 0)),
            "type": tx.get("type", "unknown"),
            "category": tx.get("category", "unknown"),
            "is_recurring": tx.get("is_recurring", False)
        }
        if expose_transaction_titles:
            clean_tx["title"] = tx.get("title", "")
        clean_txs.append(clean_tx)
        
    # Clean plans
    for plan in clean_summary.get("plans", []):
        plan.pop("id", None)
        plan.pop("user_id", None)

    clean_summary["recent_transactions"] = clean_txs
    
    return clean_summary


def build_ai_context(
    summary: Dict[str, Any],
    simulations: Dict[str, Any],
    question: str,
    user_tier: str = "free",
    conversation_history: List[Dict[str, Any]] | None = None,
) -> tuple[str, str]:
    """
    Build a (system_prompt, user_message) pair for the LLM.

    The TORA persona + schema rules go into the system role (stable across turns).
    The current financial data + question go into the user role — this keeps the
    model's attention on the actual numbers it must cite, which is critical for
    small local models that otherwise hallucinate figures.
    """

    # === SYSTEM: persona, schema, capabilities ===
    tax_features = TieringConfig.get_tax_features(user_tier)
    system = TORA_SYSTEM_PROMPT + "\n\n"
    system += "CAPABILITIES:\n"
    system += "- Autonomous Actions: YES\n"
    system += "- Memory: Unlimited conversation history\n"
    system += f"- Tax Features: {', '.join(tax_features)}\n"
    system += f"- Simulations Available: {', '.join(TieringConfig.get_simulations(user_tier))}\n"

    # === USER: ground truth FIRST, then extras, then the question ===
    category_totals = _aggregate_spending_by_category(summary.get("recent_transactions", []))
    income = summary.get("monthly_income", 0) or 0
    expenses = summary.get("monthly_expenses", 0) or 0
    balance = summary.get("account_balance", 0) or 0
    surplus = summary.get("monthly_surplus", 0) or 0
    tx_count = len(summary.get("recent_transactions", []))

    user_msg = "=== MY FINANCIAL NUMBERS (authoritative — quote these exactly) ===\n"
    user_msg += f"- Total Income: ₹{income:,.2f}\n"
    user_msg += f"- Total Expenses: ₹{expenses:,.2f}\n"
    user_msg += f"- Account Balance: ₹{balance:,.2f}\n"
    user_msg += f"- Monthly Surplus: ₹{surplus:,.2f}\n"
    user_msg += f"- Transactions on file: {tx_count}\n"
    if category_totals:
        user_msg += "- Spending by category:\n"
        for cat, amt in category_totals:
            user_msg += f"    • {cat}: ₹{amt:,.2f}\n"
    user_msg += "\n"

    extras: Dict[str, Any] = {}
    for key in ("plans", "loans", "credit_cards", "goals"):
        val = summary.get(key)
        if val:
            extras[key] = val
    if extras:
        user_msg += "ADDITIONAL CONTEXT:\n"
        user_msg += json.dumps(extras, indent=2, default=str) + "\n\n"

    if simulations:
        user_msg += "SIMULATIONS:\n"
        user_msg += json.dumps(simulations, indent=2, default=str) + "\n\n"

    if conversation_history:
        user_msg += "RECENT CONVERSATION:\n"
        for msg in conversation_history[-5:]:
            role = msg.get("role", "user").upper()
            content = str(msg.get("content", ""))[:500]
            user_msg += f"{role}: {content}\n"
        user_msg += "\n"

    user_msg += f"QUESTION: {question}\n\n"
    user_msg += (
        "Answer using ONLY the numbers above. Do not invent any figure that is "
        "not listed. Return a JSON object matching the schema from the system "
        "instructions."
    )

    return system, user_msg


def _aggregate_spending_by_category(transactions: List[Dict[str, Any]]) -> List[tuple]:
    """Sum expense transactions by category and return top entries sorted desc."""
    totals: Dict[str, float] = {}
    for tx in transactions or []:
        if tx.get("type") != "expense":
            continue
        cat = str(tx.get("category") or "uncategorized").strip() or "uncategorized"
        try:
            totals[cat] = totals.get(cat, 0.0) + float(tx.get("amount", 0) or 0)
        except (TypeError, ValueError):
            continue
    return sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:8]


# Function call_ai_api is now replaced by llm_router.call_llm


def _clean_json_response(raw_response: str) -> str:
    """Remove markdown code blocks and whitespace from AI response."""
    # Remove ```json ... ``` or ``` ... ```
    clean = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", raw_response, flags=re.DOTALL)
    return clean.strip()


def _humanize_offschema_json(data: Any, depth: int = 0) -> str:
    """Convert an off-schema JSON blob into readable markdown.

    Small LLMs (gemma4:e2b) sometimes ignore TORA's required {answer, tool_calls}
    envelope and return arbitrary JSON like {"summary": {...}, "recommendations": [...]}.
    Rather than showing raw JSON to the user, we render it as a tidy markdown list."""
    indent = "  " * depth
    if data is None:
        return ""
    if isinstance(data, (str, int, float, bool)):
        return str(data)
    if isinstance(data, list):
        if not data:
            return ""
        lines = []
        for item in data:
            rendered = _humanize_offschema_json(item, depth + 1).strip()
            if rendered:
                if "\n" in rendered:
                    lines.append(f"{indent}- {rendered.splitlines()[0]}")
                    for sub in rendered.splitlines()[1:]:
                        lines.append(f"{indent}  {sub}")
                else:
                    lines.append(f"{indent}- {rendered}")
        return "\n".join(lines)
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            label = str(key).replace("_", " ").strip().title()
            rendered = _humanize_offschema_json(value, depth + 1)
            if rendered == "":
                continue
            if isinstance(value, (dict, list)) and rendered.strip():
                lines.append(f"{indent}**{label}**")
                for sub in rendered.splitlines():
                    lines.append(sub if sub.startswith(indent) else f"{indent}  {sub}")
            else:
                lines.append(f"{indent}**{label}**: {rendered}")
        return "\n".join(lines)
    return str(data)


_USD_WORD_RE = re.compile(r"\b(?:USD|dollars?)\b", re.IGNORECASE)


def _rupee_ize(value: Any) -> Any:
    """Recursively replace $ / USD / 'dollars' with ₹ in any string value."""
    if isinstance(value, str):
        # $1,234 or $ 1234.5 -> ₹1,234 / ₹ 1234.5
        replaced = re.sub(r"\$\s?", "₹", value)
        replaced = _USD_WORD_RE.sub("rupees", replaced)
        return replaced
    if isinstance(value, dict):
        return {k: _rupee_ize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_rupee_ize(v) for v in value]
    return value


async def generate_financial_strategy(user_id: int, question: str, model: str = "tora", user_tier: str = "free") -> Dict[str, Any]:
    """
    The orchestrator function executing the full Agent Workflow with tier awareness.
    1. Fetches user financial summary
    2. Runs simulations (tier-specific)
    3. Sanitizes data (tier-specific)
    4. Loads conversation history (tier-limited)
    5. Builds context and calls LLM
    """
    # 1. Fetch (Now async via MCP)
    raw_summary = await fetch_financial_summary(user_id)
    if not raw_summary:
        return {"error": "Could not fetch user financial summary."}
        
    # 2. Simulate (tier-aware)
    simulations = run_financial_simulations(raw_summary, user_tier)
    
    # 3. Sanitize (tier-aware)
    clean_summary = sanitize_financial_data(raw_summary, user_tier)
    
    # 4. Load conversation history (tier-aware memory limits)
    try:
        conversation_history = _load_recent_conversation(user_id, user_tier)
        logger.info(f"Loaded {len(conversation_history)} conversation messages for tier {user_tier}")
    except Exception as e:
        logger.warning(f"Could not load conversation history: {e}")
        conversation_history = []
    
    # 5. Contextualize (tier-aware with memory injection)
    system_prompt, user_message = build_ai_context(
        clean_summary, simulations, question, user_tier, conversation_history
    )

    # 6. Execute
    try:
        raw_response = call_llm(model, user_message, clean_summary, system_prompt=system_prompt)
        
        # Clean and parse the structured JSON response
        try:
            clean_response = _clean_json_response(raw_response)
            structured_advice = json.loads(clean_response)
            
            # Execute tools if requested (respecting tier-based autonomy)
            can_act = TieringConfig.can_act_autonomously(user_tier)
            
            if "tool_calls" in structured_advice and isinstance(structured_advice["tool_calls"], list):
                registry = get_tool_registry()
                for tool in structured_advice["tool_calls"]:
                    try:
                        name = tool.get("name")
                        params = tool.get("parameters", {})
                        
                        # Check if tier requires confirmation for this action
                        requires_confirm = TieringConfig.requires_action_confirmation(user_tier, name)
                        
                        # Free tier always requires confirmation; Pro tier can auto-execute
                        # (unless specifically marked as requiring confirmation)
                        if requires_confirm and not can_act:
                            logger.info(f"Tool {name} requires confirmation for {user_tier} tier user")
                            # Modify response to indicate user action needed
                            tool["status"] = "pending_confirmation"
                            continue
                        
                        if name in registry:
                            logger.info(f"TORA executing tool: {name} for user {user_id} (tier={user_tier})")
                            tool_func = registry[name]
                            
                            if name in ["create_plan", "create_loan_repayment_plan"]:
                                tool_func(user_id, params)
                            elif name == "adjust_plan":
                                plan_id = params.pop("plan_id", None)
                                if plan_id:
                                    tool_func(user_id, plan_id, params)
                        else:
                            logger.warning(f"Unknown tool requested by TORA: {name}")
                    except Exception as e:
                        logger.error(f"Error executing TORA tool {tool}: {e}")
            
            # Unwrap the 'answer' envelope if present
            answer_content = structured_advice.get("answer", structured_advice)

            # 7. Post-process based on response mode.
            #    The LLM may return one of:
            #      a) a plain string (legacy simple mode)
            #      b) {"mode":"simple","content":"..."}
            #      c) {"Financial Overview":..., "Current Position":..., ...}
            structured_keys = ("Financial Overview", "Current Position", "Recommended Strategy", "Expected Outcome")

            if isinstance(answer_content, str):
                # (a) Plain string → simple mode
                final_output = {"mode": "simple", "content": answer_content}

            elif isinstance(answer_content, dict) and (
                answer_content.get("mode") == "simple" or
                (isinstance(answer_content.get("content"), str) and
                 not any(k in answer_content for k in structured_keys))
            ):
                # (b) Explicit simple mode
                final_output = {
                    "mode": "simple",
                    "content": str(answer_content.get("content", "")).strip(),
                }

            elif isinstance(answer_content, dict):
                # (c) Structured mode — keep only populated 4-section keys
                sections = {
                    k: answer_content[k]
                    for k in structured_keys
                    if answer_content.get(k) and answer_content[k] != "N/A"
                }
                if sections:
                    final_output = sections
                else:
                    # Model returned off-schema JSON — humanize into markdown instead of dumping raw JSON
                    content_val = answer_content.get("content")
                    if isinstance(content_val, str) and content_val.strip():
                        fallback_text = content_val
                    else:
                        fallback_text = _humanize_offschema_json(answer_content)
                    final_output = {"mode": "simple", "content": str(fallback_text).strip()}
            else:
                final_output = {"mode": "simple", "content": str(answer_content)}
            
            # Normalize currency: convert any $ / USD / dollars into ₹
            final_output = _rupee_ize(final_output)

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


def _load_recent_conversation(user_id: int, user_tier: str = "free") -> List[Dict[str, Any]]:
    """
    Load conversation history respecting tier-based memory limits.
    
    Args:
        user_id: User ID
        user_tier: "free" (5 turns), "pro" (unlimited), "enterprise" (unlimited+metadata)
    
    Returns:
        List of recent conversation turns with 'role' and 'content' keys.
    """
    # Get tier-specific limit (5 for free, None/unlimited for pro/enterprise)
    limit = get_tier_memory_limit(user_tier)
    if limit is None:
        limit = 1000  # Safety max even for unlimited tiers
    
    try:
        data = call_finance_internal("tora-conversation", user_id, {"limit": limit})
        if not data or not isinstance(data, list):
            logger.debug(f"No conversation history found for user {user_id}")
            return []
        
        history = []
        for msg in data:
            history.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
                "timestamp": msg.get("created_at"),
            })
        
        stats = format_memory_stats(user_tier, len(history))
        logger.info(f"Loaded conversation history - {stats}")
        return history
        
    except Exception as e:
        logger.warning(f"Error loading conversation history for user {user_id}: {e}")
        return []


async def handle_user_question(user_id: int, question: str, model: str = "tora", user_tier: str = "free") -> Dict[str, Any]:
    """
    Main entry point for the TORA agent endpoint with tiering support.
    1. Detects message intent (greeting, finance, or other).
    2. Routes to local responses or AI workflow based on tier capabilities.
    3. Persists conversation history for memory across sessions.
    """

    # 1. Intent Detection
    intent = detect_intent(question)

    def _summary_text(resp: Dict[str, Any]) -> str:
        """Derive a short plain-text summary of any reply for conversation storage."""
        if resp.get("mode") == "simple":
            return resp.get("content", "")
        return resp.get("Financial Overview", "") or resp.get("content", "")

    # A follow-up like "for instance?", "why", "tell me more" has no finance
    # keyword but continues the prior thread. If the user already has a
    # conversation history, we should NEVER drop them into a canned non-finance
    # fallback — route everything to the LLM with the history as context.
    has_prior_conversation = False
    try:
        prior = _load_recent_conversation(user_id, user_tier)
        has_prior_conversation = len(prior) > 0
    except Exception:
        has_prior_conversation = False

    # Short follow-ups (<= 4 words) in an active chat always go to the LLM.
    is_short_followup = has_prior_conversation and len(question.split()) <= 4

    # Pure greetings and small-talk are ALWAYS handled by canned replies —
    # we never want a "hi" to trigger a financial data dump, even mid-chat.
    if intent == "greeting":
        logger.info(f"Greeting detected: {question}")
        response = json.loads(get_greeting_response(is_returning=has_prior_conversation))
        _save_conversation(user_id, "user", question)
        _save_conversation(user_id, "assistant", _summary_text(response), response)
        return response

    if intent == "small_talk":
        logger.info(f"Small-talk detected: {question}")
        response = json.loads(get_small_talk_response(question))
        _save_conversation(user_id, "user", question)
        _save_conversation(user_id, "assistant", _summary_text(response), response)
        return response

    if intent == "conversational" and not has_prior_conversation:
        # First-turn capability question → canned capability card
        capability_pattern = re.compile(
            r'what\s+can\s+you\s+do|what\s+do\s+you\s+do|who\s+are\s+you|'
            r'what\s+are\s+you|your\s+feature|your\s+capabilit|what\s+else|'
            r'get\s+started|how\s+do\s+i\s+use',
            re.IGNORECASE
        )
        if capability_pattern.search(question):
            logger.info(f"Capability question detected: {question}")
            response = json.loads(get_capability_response())
            _save_conversation(user_id, "user", question)
            _save_conversation(user_id, "assistant", _summary_text(response), response)
            return response
        logger.info(f"Conversational query routed to LLM: {question}")

    if intent == "non_finance_query" and not has_prior_conversation and not is_short_followup:
        logger.info(f"Non-financial query detected: {question}")
        response = json.loads(get_fallback_response())
        _save_conversation(user_id, "user", question)
        _save_conversation(user_id, "assistant", _summary_text(response), response)
        return response

    # Otherwise: the user is mid-conversation or asked a finance question —
    # fall through to the full LLM path with context + history injected.

    # 2. Proceed with financial intelligence lifecycle for 'finance_query' and 'conversational'
    # Save the user turn first
    _save_conversation(user_id, "user", question)

    try:
        strategy_json = await generate_financial_strategy(user_id, question, model, user_tier)
        # Persist the assistant response
        save_content = strategy_json.get("Financial Overview") or strategy_json.get("content") or ""
        _save_conversation(user_id, "assistant", save_content, strategy_json)
        return strategy_json
    except Exception as e:
        logger.error(f"TORA execution failed: {str(e)}")
        raise
