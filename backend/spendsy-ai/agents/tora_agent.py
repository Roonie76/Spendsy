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
from .tora_personality import (
    TORA_SYSTEM_PROMPT,
    detect_ambiguous_goal,
    detect_intent,
    get_ambiguous_goal_response,
    get_capability_response,
    get_fallback_response,
    get_greeting_response,
    get_small_talk_response,
)
from .llm_router import call_llm
from .tools.tool_registry import get_tool_registry
from mcp_connector import fetch_context_via_mcp
from vault.vault_sync import sync_vault_after_session, read_vault_context
from .tora import (
    resolve_and_fetch,
    build_market_context_block,
    audit_structured_output,
    summarize_fetch_outcome,
    should_enable_thinking,
)
from .tora.expert_router import inject_expert_preamble
from .tora.context_compressor import (
    compress_transactions,
    compact_extras,
    compress_history,
    compress_trends,
)

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
        "recent_transactions": context.get("recent_transactions", []),
        "monthly_trends": context.get("monthly_trends", []),
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
            monthly_rate = float(loan.get("interest_rate", 10.5)) / 100.0 / 12.0
            emi = float(loan.get("emi_amount", loan.get("principal_amount", principal) * 0.05))

            if principal <= 0 or surplus <= 0 or emi <= 0:
                continue

            try:
                standard_months = _months_to_payoff(principal, emi, monthly_rate)
                accelerated_months = _months_to_payoff(principal, emi + surplus, monthly_rate)
                months_saved = max(0, int(round(standard_months - accelerated_months)))
                interest_saved = max(
                    0.0,
                    (standard_months * emi) - (accelerated_months * (emi + surplus))
                )

                simulations["loan_optimizations"].append({
                    "loan_type": loan.get("loan_type", "unknown"),
                    "interest_rate_pct": round(monthly_rate * 12 * 100, 2),
                    "extra_payment_scenario": float(surplus),
                    "estimated_months_saved": months_saved,
                    "estimated_interest_saved": round(interest_saved, 2),
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
    user_id: int | None = None,
    market_block: str = "",
) -> tuple[str, str]:
    """
    Build a (system_prompt, user_message) pair for the LLM.

    Ordering strategy (matters a lot for small models):
      1. Conversation history FIRST — sets the thread so follow-ups ("why?",
         "for instance?") resolve correctly. Placed early so it's not
         mistaken for the current question.
      2. Financial numbers in the MIDDLE — stable reference the model will
         quote verbatim.
      3. Simulations + extras after the numbers.
      4. Market/category enrichment (from universal intelligence engine)
         before the question, so track 2 queries have grounded facts.
      5. Current question LAST, immediately followed by a compact reasoning
         checklist. Recency bias means the model pays most attention to
         these final lines, so they steer the reply shape.
    """

    # === SYSTEM: persona, schema, capabilities ===
    tax_features = TieringConfig.get_tax_features(user_tier)
    system = TORA_SYSTEM_PROMPT + "\n\n"
    system += "CAPABILITIES:\n"
    system += f"- Tier: {user_tier}\n"
    system += f"- Autonomous Actions: {'YES' if TieringConfig.can_act_autonomously(user_tier) else 'NO (tool calls require user confirmation)'}\n"
    system += "- Memory: persistent conversation history across sessions\n"
    system += f"- Tax Features: {', '.join(tax_features) or 'none'}\n"
    system += f"- Simulations Available: {', '.join(TieringConfig.get_simulations(user_tier)) or 'none'}\n"

    # === USER MESSAGE ===
    user_msg = ""

    # 1. Conversation history FIRST - MLA-inspired compression.
    valid_history = [m for m in conversation_history if str(m.get("content", "")).strip() and str(m.get("content", "")).strip() != "{}"]
    if valid_history:
        compressed_hist = compress_history(valid_history, keep_recent=3)
        if compressed_hist:
            user_msg += compressed_hist

    # 2. Vault-first context injection.
    #    Structured prose with ₹ amounts already formatted is dramatically
    #    easier for gemma4:e2b than nested JSON. Fall back to raw numbers
    #    if the vault isn't populated yet.
    vault_context = read_vault_context(user_id) if user_id else ""

    if vault_context:
        user_msg += "=== MY FINANCIAL PROFILE (from personal vault) ===\n"
        user_msg += vault_context + "\n\n"
    else:
        # Fallback: build raw numbers block from summary dict
        category_totals = _aggregate_spending_by_category(summary.get("recent_transactions", []))
        income = summary.get("monthly_income", 0) or 0
        expenses = summary.get("monthly_expenses", 0) or 0
        balance = summary.get("account_balance", 0) or 0
        surplus = summary.get("monthly_surplus", 0) or 0
        tx_count = len(summary.get("recent_transactions", []))

        user_msg += "=== MY FINANCIAL NUMBERS (authoritative — quote these exactly) ===\n"
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

    # 2b. Recent Transactions - MLA-inspired compression.
    recent_txs = summary.get("recent_transactions", [])
    if recent_txs:
        compressed_txs = compress_transactions(recent_txs, max_items=15)
        if compressed_txs:
            user_msg += compressed_txs + "\n"

    # 2c. 6-month trend block (compact — MoM deltas and anomalies only).
    trend_block = _summarize_trends(summary.get("monthly_trends", []) or [])
    if trend_block:
        user_msg += "=== 6-MONTH TRENDS (for detecting shifts; only cite numbers that appear above) ===\n"
        user_msg += compress_trends(trend_block) + "\n\n"

    # 3. Extras + simulations - MLA-inspired JSON compaction.
    extras: Dict[str, Any] = {}
    for key in ("plans", "loans", "credit_cards", "goals"):
        val = summary.get(key)
        if val:
            extras[key] = val
    if extras:
        compacted = compact_extras(extras)
        if compacted:
            user_msg += compacted + "\n"
        else:
            user_msg += "ADDITIONAL CONTEXT:\n"
            user_msg += json.dumps(extras, indent=2, default=str) + "\n\n"

    if simulations:
        user_msg += "SIMULATIONS:\n"
        user_msg += json.dumps(simulations, indent=2, default=str) + "\n\n"

    # 4. Market/category enrichment from the universal intelligence engine.
    #    Only present for track 2 queries where a plugin matched; track 1
    #    profile-only questions skip this block entirely.
    if market_block:
        user_msg += "=== MARKET & CATEGORY CONTEXT (use these grounded facts for decisions) ===\n"
        user_msg += market_block + "\n\n"

    # 5. Question + compact reasoning checklist last (recency-biased steering).
    user_msg += f"QUESTION: {question}\n\n"
    user_msg += (
        "Before you reply, think step-by-step in the 'reasoning' field of the JSON.\n"
        "1. Every ₹ figure and % you quote MUST appear verbatim in a block above. "
        "If it isn't there, DELETE the sentence — don't guess a number.\n"
        "2. If the user asked a decision question (\"should I\", \"can I afford\", "
        "\"is now a good time\"), your answer must be a clear decision or "
        "recommendation, not a data dump. Use the Rules in the MARKET block.\n"
        "3. Default to simple mode. Only use structured mode when asked to summarize, "
        "analyze, plan, or review.\n"
        "Return a single valid JSON object matching the schema."
    )

    return system, user_msg


def _summarize_trends(trends: List[Dict[str, Any]]) -> str:
    """Render 6-month trends as a compact text block for the prompt.

    Design choice: raw `FinancialInsight` JSON is too verbose to send to a
    small model. We surface only:
      - month-over-month income / expense / savings deltas
      - top 3 categories by latest-month expense
      - categories that shifted ≥30% MoM (the anomaly trigger)

    Returns "" when there's no trend data — the caller should skip the
    section entirely so we don't waste tokens on empty headers.
    """
    if not trends or len(trends) < 2:
        return ""

    latest = trends[-1]
    prior = trends[-2]

    def _pct_delta(now: float, then: float) -> str:
        if then == 0:
            return "n/a" if now == 0 else "new"
        return f"{((now - then) / then) * 100:+.0f}%"

    lines = [f"Trend window: {trends[0]['period']} → {latest['period']} ({len(trends)} months)"]
    lines.append(
        f"Latest month ({latest['period']}): income ₹{latest['total_income']:,.0f}, "
        f"expense ₹{latest['total_expense']:,.0f}, net ₹{latest['net_savings']:,.0f}"
    )
    lines.append(
        f"  vs prior month: income {_pct_delta(latest['total_income'], prior['total_income'])}, "
        f"expense {_pct_delta(latest['total_expense'], prior['total_expense'])}, "
        f"net {_pct_delta(latest['net_savings'], prior['net_savings'])}"
    )

    latest_cats = latest.get("by_category") or {}
    prior_cats = prior.get("by_category") or {}
    top_cats = sorted(latest_cats.items(), key=lambda kv: float(kv[1] or 0), reverse=True)[:3]
    if top_cats:
        lines.append("Top categories this month:")
        for cat, amt in top_cats:
            lines.append(f"    • {cat}: ₹{float(amt or 0):,.0f}")

    anomalies = []
    for cat, now_amt in latest_cats.items():
        now_f = float(now_amt or 0)
        then_f = float(prior_cats.get(cat, 0) or 0)
        if then_f <= 0:
            continue
        delta = (now_f - then_f) / then_f
        if abs(delta) >= 0.30 and now_f >= 500:  # Ignore trivial absolute amounts
            anomalies.append((cat, delta, now_f, then_f))
    if anomalies:
        anomalies.sort(key=lambda t: abs(t[1]), reverse=True)
        lines.append("MoM shifts ≥30%:")
        for cat, delta, now_f, then_f in anomalies[:4]:
            lines.append(
                f"    • {cat}: ₹{then_f:,.0f} → ₹{now_f:,.0f} ({delta*100:+.0f}%)"
            )

    return "\n".join(lines)


def _months_to_payoff(principal: float, payment: float, monthly_rate: float) -> float:
    """Months to fully repay `principal` at fixed `payment` and `monthly_rate`.

    Uses the standard amortization inversion:
        n = -log(1 - r*P/M) / log(1 + r)
    Falls back to simple division when the rate is effectively zero, and
    returns infinity when the payment can't cover the monthly interest
    (loan would never be paid off at that payment level).
    """
    import math
    if principal <= 0 or payment <= 0:
        return 0.0
    if monthly_rate <= 0:
        return principal / payment
    interest_only = principal * monthly_rate
    if payment <= interest_only:
        return float("inf")
    return -math.log(1 - (monthly_rate * principal / payment)) / math.log(1 + monthly_rate)


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


_CONFIDENCE_RE = re.compile(r"CONFIDENCE:\s*(0(?:\.\d+)?|1(?:\.0+)?)", re.IGNORECASE)


def _extract_confidence(reasoning: str) -> float:
    """Extract self-reported confidence from the model's reasoning field."""
    if not reasoning:
        return 0.0
    match = _CONFIDENCE_RE.search(reasoning)
    if match:
        try:
            return float(match.group(1))
        except (ValueError, TypeError):
            return 0.0
    certainty_markers = ("therefore the answer is", "in conclusion", "this confirms", "i am confident")
    if any(marker in reasoning.lower() for marker in certainty_markers):
        return 0.7
    return 0.0


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


# Matches "USD 1,234", "USD1234", "1,234 USD", "1,234 dollars", "500 dollar" etc.
# Capture group isolates the number so we can reconstruct it with a ₹ prefix.
_USD_NUM_PREFIX_RE = re.compile(r"\bUSD\s*([\d,]+(?:\.\d+)?)", re.IGNORECASE)
_USD_NUM_SUFFIX_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(?:USD|dollars?)\b", re.IGNORECASE)
_USD_WORD_RE = re.compile(r"\b(?:USD|dollars?)\b", re.IGNORECASE)


def _rupee_ize(value: Any) -> Any:
    """Recursively replace $ / USD / 'dollars' with the ₹ symbol in strings.

    Order matters: resolve number-bearing phrases first so the number itself
    gets the ₹ prefix, then strip any bare USD/dollar words that remain.
    """
    if isinstance(value, str):
        # "$1,234" / "$ 1234.5" -> "₹1,234" / "₹1234.5"
        replaced = re.sub(r"\$\s?", "₹", value)
        # "USD 500" / "USD500" -> "₹500"
        replaced = _USD_NUM_PREFIX_RE.sub(r"₹\1", replaced)
        # "500 USD" / "500 dollars" -> "₹500"
        replaced = _USD_NUM_SUFFIX_RE.sub(r"₹\1", replaced)
        # Any remaining bare "USD" / "dollars" with no adjacent number
        replaced = _USD_WORD_RE.sub("₹", replaced)
        return replaced
    if isinstance(value, dict):
        return {k: _rupee_ize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_rupee_ize(v) for v in value]
    return value


_SEBI_KEYWORDS_RE = re.compile(
    r"\b(?:invest(?:ment|ing|or)?|SIP|NPS|mutual\s+fund|equity|stock|share|portfolio|MF|ETF|index\s+fund|ELSS|bond|debenture|securities)\b",
    re.IGNORECASE,
)

_SEBI_DISCLAIMER = (
    "\n\n---\n*Disclaimer: This is general information, not investment advice. "
    "Consult a SEBI-registered advisor before making investment decisions.*"
)


def _sebi_disclaim(output: Any) -> Any:
    """Append a brief SEBI disclaimer if the response mentions investments.

    Operates on the final_output dict. Only touches string `content` values
    and the four structured-mode section values — never adds a disclaimer
    to error messages or tool-call metadata.
    """
    if not isinstance(output, dict):
        return output

    # Collect all text values we should scan
    texts_to_scan: list[str] = []
    if output.get("mode") == "simple":
        texts_to_scan.append(str(output.get("content", "")))
    else:
        for key in ("Financial Overview", "Recommended Strategy", "Expected Outcome"):
            val = output.get(key)
            if isinstance(val, str):
                texts_to_scan.append(val)

    combined = " ".join(texts_to_scan)
    if not _SEBI_KEYWORDS_RE.search(combined):
        return output

    # Append disclaimer to the last visible text field
    if output.get("mode") == "simple":
        content = str(output.get("content", ""))
        if _SEBI_DISCLAIMER.strip() not in content:
            output["content"] = content + _SEBI_DISCLAIMER
    else:
        # Structured mode: append to the last non-empty section
        for key in reversed(("Expected Outcome", "Recommended Strategy", "Current Position", "Financial Overview")):
            val = output.get(key)
            if isinstance(val, str) and val.strip() and val != "N/A":
                if _SEBI_DISCLAIMER.strip() not in val:
                    output[key] = val + _SEBI_DISCLAIMER
                break

    return output


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

    # 4b. Universal Intelligence Engine — resolve entities, fetch plugin data.
    #     Track 1 queries ("how much did I spend on food") return no matches
    #     and `market_block` stays empty; track 2 queries ("can I afford a
    #     car") get ~200-500 tokens of grounded enrichment.
    market_block = ""
    try:
        user_surplus = float(clean_summary.get("monthly_surplus", 0) or 0)
        fetch_results = await resolve_and_fetch(question, user_surplus=user_surplus)
        if fetch_results:
            market_block = build_market_context_block(fetch_results)
            logger.info(
                "Universal Intelligence Engine resolved %s",
                summarize_fetch_outcome(fetch_results),
            )
    except Exception as e:
        logger.warning(f"Universal engine failed, continuing without enrichment: {e}")
        market_block = ""

    # 5. Contextualize (tier-aware with memory injection + market enrichment)
    system_prompt, user_message = build_ai_context(
        clean_summary, simulations, question, user_tier, conversation_history,
        user_id=user_id,
        market_block=market_block,
    )

    # 5b. MoE-inspired expert routing: prepend domain-specific preamble.
    system_prompt, expert_id = inject_expert_preamble(system_prompt, question)
    if expert_id:
        logger.info("Expert router activated: %s", expert_id)

    # 6. Execute
    # Thinking mode is ON when the query is a track 2 decision (plugin matched)
    # or the message shows comparison/hypothetical/planning language.
    thinking_enabled = should_enable_thinking(
        question, has_plugin_match=bool(market_block)
    )
    logger.info(
        "Thinking mode %s for this query",
        "ENABLED" if thinking_enabled else "disabled",
    )
    # === RECURRENT REASONING LOOP (OpenMythos Recurrent-Depth) ===
    max_loops = 3 if thinking_enabled else 1
    current_loop = 0
    raw_response = ""
    structured_advice = {}
    accumulated_tool_results = []
    _CONF_THRESH = 0.85

    try:
      while current_loop < max_loops:
        current_loop += 1
        loop_name = f"Loop {current_loop}/{max_loops}" if thinking_enabled else "Single Pass"
        try:
            loop_sys = system_prompt
            if current_loop > 1:
                loop_sys += (
                    f"\n\n[RECURRENT REFINEMENT - {loop_name}]\n"
                    "Review previous reasoning and tool outputs.\n"
                    "Check numeric consistency.\n"
                    "End reasoning with: CONFIDENCE: 0.XX (0.0-1.0).\n"
                )
                if accumulated_tool_results:
                    user_message += "\n\n=== TOOL OUTPUTS (previous loop) ===\n"
                    user_message += json.dumps(accumulated_tool_results, indent=2)
            raw_response = call_llm(
                model, user_message, clean_summary,
                system_prompt=loop_sys, thinking=thinking_enabled,
            )
        except Exception as e:
            logger.error(f"LLM call failed in {loop_name}: {e}")
            if current_loop == 1:
                raise
            break

        try:
            clean_response = _clean_json_response(raw_response)
            structured_advice = json.loads(clean_response)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {loop_name}")
            if current_loop == 1:
                return {
                    "mode": "simple",
                    "content": "I had trouble formatting that answer. Could you rephrase?",
                    "error": "AI returned malformed structured data."
                }
            break

        # Confidence-gated early exit
        if thinking_enabled and current_loop < max_loops:
            conf = _extract_confidence(structured_advice.get("reasoning", ""))
            logger.info("Recurrent loop %d confidence: %.2f", current_loop, conf)
            if conf >= _CONF_THRESH and not structured_advice.get("tool_calls"):
                logger.info("Early exit at loop %d (confidence %.2f)", current_loop, conf)
                break

        # Execute tools if requested
        can_act = TieringConfig.can_act_autonomously(user_tier)
        tool_calls = structured_advice.get("tool_calls", [])
        if tool_calls and isinstance(tool_calls, list):
            registry = get_tool_registry()
            loop_tool_results = []
            for tool in tool_calls:
                try:
                    name = tool.get("name")
                    params = tool.get("parameters", {})
                    requires_confirm = TieringConfig.requires_action_confirmation(user_tier, name)
                    if requires_confirm and not can_act:
                        logger.info(f"Tool {name} requires confirmation for {user_tier} tier")
                        tool["status"] = "pending_confirmation"
                        continue
                    if name in registry:
                        logger.info(f"TORA executing tool: {name} for user {user_id}")
                        tool_func = registry[name]
                        if name in ["create_plan", "create_loan_repayment_plan"]:
                            result = tool_func(user_id, params)
                        elif name == "adjust_plan":
                            plan_id = params.pop("plan_id", None)
                            result = tool_func(user_id, plan_id, params) if plan_id else "missing plan_id"
                        else:
                            result = tool_func(user_id, **params)
                        loop_tool_results.append({"tool": name, "result": str(result)})
                    else:
                        logger.warning(f"Unknown tool requested by TORA: {name}")
                except Exception as e:
                    logger.error(f"Error executing TORA tool {tool}: {e}")
            if loop_tool_results:
                accumulated_tool_results.extend(loop_tool_results)
                continue
        break  # No tool calls; exit loop

      # --- Post-processing ---
      answer_content = structured_advice.get("answer", structured_advice)

      structured_keys = ("Financial Overview", "Current Position", "Recommended Strategy", "Expected Outcome")
      if isinstance(answer_content, str):
          final_output = {"mode": "simple", "content": answer_content}
      elif isinstance(answer_content, dict) and (
          answer_content.get("mode") == "simple" or
          (isinstance(answer_content.get("content"), str) or isinstance(answer_content.get("text"), str)) and
           not any(k in answer_content for k in structured_keys)
      ):
          content_str = answer_content.get("content") or answer_content.get("text") or ""
          final_output = {"mode": "simple", "content": str(content_str).strip()}
      elif isinstance(answer_content, dict):
          sections = {k: answer_content[k] for k in structured_keys if answer_content.get(k) and answer_content[k] != "N/A"}
          if sections:
              final_output = sections
          else:
              content_val = answer_content.get("content")
              fallback_text = content_val if isinstance(content_val, str) and content_val.strip() else _humanize_offschema_json(answer_content)
              final_output = {"mode": "simple", "content": str(fallback_text).strip()}
      else:
          final_output = {"mode": "simple", "content": str(answer_content)}

      final_output = _rupee_ize(final_output)
      if market_block:
          final_output, audit_warnings = audit_structured_output(final_output, user_message)
          if audit_warnings:
              logger.info("Number auditor hedged %d figure(s): %s", len(audit_warnings), audit_warnings[:5])
      final_output = _sebi_disclaim(final_output)
      if thinking_enabled:
          logger.info("Recurrent loop: %d/%d passes, expert=%s", current_loop, max_loops, expert_id or "general")
      return final_output

    except Exception as e:
        logger.error(f"TORA execution failed: {e}")
        return {"mode": "simple", "content": "I hit a technical snag. Give it another try in a moment."}


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

    # Deterministic ambiguity pre-filter — catches obvious "I want to save more"
    # style asks before we spend tokens on the LLM. Only fires on first-turn
    # or non-follow-up messages so we don't short-circuit a legitimate thread.
    if intent == "finance_query" and not is_short_followup:
        canned = detect_ambiguous_goal(question)
        if canned is not None:
            logger.info(f"Ambiguous goal detected — returning clarifier: {question!r}")
            response = json.loads(get_ambiguous_goal_response(question))
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

        # Sync vault (fire-and-forget — never blocks the response)
        try:
            raw_summary = await fetch_financial_summary(user_id)
            if raw_summary:
                clean = sanitize_financial_data(raw_summary, user_tier)
                await sync_vault_after_session(
                    user_id=user_id,
                    clean_summary=clean,
                    question=question,
                    answer=strategy_json,
                    intent=intent,
                    user_tier=user_tier,
                )
        except Exception as ve:
            logger.warning(f"Vault sync skipped: {ve}")

        return strategy_json
    except Exception as e:
        logger.error(f"TORA execution failed: {str(e)}")
        raise
