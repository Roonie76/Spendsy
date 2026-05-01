"""
Evaluator — Phase 4 AI trainer loop.

Scores each TORA response after it's sent to the user (async, non-blocking).
Composite score 0.0-1.0 from 4 dimensions:

  goal_addressed     0.35  — did response answer the detected goal type?
  numbers_audited    0.30  — did number_auditor pass? (no hallucinated ₹/%)
  compliance_passed  0.20  — did compliance_filter approve?
  user_feedback      0.15  — thumbs up (+1.0), thumbs down (0.0), none (0.5)

Threshold: score >= 0.75 → winning trace → stored in reasoning_store.
Called from tora_agent as a background asyncio.Task (never awaited inline).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

WINNING_THRESHOLD = 0.75

WEIGHTS = {
    "goal_addressed":  0.35,
    "numbers_audited": 0.30,
    "compliance":      0.20,
    "user_feedback":   0.15,
}


@dataclass
class EvalResult:
    score: float
    is_winner: bool
    dimensions: dict[str, float]
    query: str
    response_preview: str
    goal_type: str
    evaluated_at: str


def _score_goal_addressed(query: str, response_text: str, goal_type: str) -> float:
    """
    Check if response substantively addresses the detected goal.
    Heuristic: goal-specific keywords must appear in response.
    """
    if not response_text or not query:
        return 0.5

    goal_keywords: dict[str, list[str]] = {
        "car":        ["emi", "loan", "on-road", "down payment", "rate"],
        "house":      ["home loan", "emi", "down payment", "80c", "24b", "interest"],
        "invest":     ["sip", "return", "cagr", "corpus", "fund", "ppf", "elss"],
        "loan_repay": ["prepay", "avalanche", "snowball", "interest saved", "tenure"],
        "tax":        ["regime", "deduction", "80c", "tax", "refund", "surcharge"],
        "wedding":    ["budget", "save", "emi", "plan", "months"],
        # travel: broader set — short trips won't always mention forex/insurance
        "travel":     ["budget", "save", "trip", "cost", "spend", "travel"],
        "education":  ["emi", "loan", "save", "corpus", "months"],
        "retirement": ["corpus", "nps", "ppf", "sip", "retire"],
        # emergency: appliance / medical emergencies don't always say "fund" literally
        "emergency":  ["months", "save", "liquid", "cost", "cover"],
        "generic":    [],
    }

    # --- Query-content fallback scoring ---
    # If goal_type is generic but query signals a specific intent, use that keyword set
    _QUERY_GOAL_HINTS: dict[str, list[str]] = {
        # English
        "appliance":    ["cost", "emi", "pay", "save", "purchase", "buy"],
        "gadget":       ["cost", "emi", "pay", "save", "purchase", "buy"],
        "salary":       ["save", "invest", "allocate", "fund", "emi", "budget"],
        "trip":         ["cost", "save", "spend", "budget", "travel"],
        "vacation":     ["cost", "save", "spend", "budget", "travel"],
        # Hinglish triggers → map to response keywords
        "lena hai":     ["cost", "emi", "pay", "save", "purchase"],
        "kharidna":     ["cost", "emi", "pay", "save", "purchase"],
        "kitna hoga":   ["cost", "emi", "pay", "budget"],
        "manage karoon":["save", "budget", "emi", "cost", "pay"],
        "afford":       ["emi", "budget", "cost", "save", "pay"],
        "cibil":        ["cibil", "score", "credit", "loan", "months"],
        "regime":       ["tax", "regime", "deduction", "80c", "refund"],
        "retire":       ["corpus", "nps", "ppf", "sip", "retire"],
        "insurance":    ["months", "save", "cost", "cover", "premium"],
        "operation":    ["cost", "save", "cover", "fund", "liquid"],
        "shaadi":       ["budget", "save", "emi", "plan", "months"],
        "goa":          ["budget", "save", "trip", "cost", "spend"],
        "manali":       ["budget", "save", "trip", "cost", "spend"],
        "europe":       ["budget", "save", "trip", "cost", "spend"],
        "swift":        ["emi", "loan", "on-road", "down payment", "rate"],
        "nexon":        ["emi", "loan", "on-road", "down payment", "rate"],
    }
    keywords = goal_keywords.get(goal_type, [])

    if not keywords:
        # For generic goal_type, try to infer from query content
        if goal_type == "generic":
            q_lower = query.lower()
            for hint_key, hint_kws in _QUERY_GOAL_HINTS.items():
                if hint_key in q_lower:
                    keywords = hint_kws
                    break
        if not keywords:
            return 0.7   # truly generic — can't validate precisely

    resp_lower = response_text.lower()
    hits = sum(1 for kw in keywords if kw in resp_lower)
    return min(1.0, hits / max(len(keywords) * 0.5, 1))


def _score_numbers_audited(audit_warnings: list[str]) -> float:
    """
    0 warnings → 1.0. Each warning reduces score by 0.2. Floor at 0.0.
    """
    return max(0.0, 1.0 - len(audit_warnings) * 0.20)


def _score_compliance(compliance_result: dict) -> float:
    """
    compliance_filter output: {passed: bool, flags: list}.
    passed=True + 0 flags → 1.0.
    passed=True + flags → 0.7.
    passed=False → 0.2.
    """
    if not compliance_result:
        return 0.5
    passed = compliance_result.get("passed", True)
    flags  = compliance_result.get("flags", [])
    if not passed:
        return 0.2
    return 1.0 if not flags else 0.7


def _score_user_feedback(feedback_rating: Optional[str]) -> float:
    """thumbs_up → 1.0 | thumbs_down → 0.0 | None → 0.5 (neutral)."""
    if feedback_rating == "up":
        return 1.0
    if feedback_rating == "down":
        return 0.0
    return 0.5


def evaluate(
    query: str,
    response_text: str,
    goal_type: str = "generic",
    audit_warnings: Optional[list[str]] = None,
    compliance_result: Optional[dict] = None,
    user_feedback: Optional[str] = None,
) -> EvalResult:
    """
    Score a TORA response synchronously.
    Called from the async wrapper below.
    """
    dims = {
        "goal_addressed":  _score_goal_addressed(query, response_text, goal_type),
        "numbers_audited": _score_numbers_audited(audit_warnings or []),
        "compliance":      _score_compliance(compliance_result or {}),
        "user_feedback":   _score_user_feedback(user_feedback),
    }

    score = sum(WEIGHTS[k] * v for k, v in dims.items())
    score = round(score, 4)

    return EvalResult(
        score=score,
        is_winner=score >= WINNING_THRESHOLD,
        dimensions={k: round(v, 3) for k, v in dims.items()},
        query=query,
        response_preview=response_text[:200],
        goal_type=goal_type,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )



async def evaluate_async(
    query: str,
    response_text: str,
    goal_type: str = "generic",
    audit_warnings: Optional[list[str]] = None,
    compliance_result: Optional[dict] = None,
    user_feedback: Optional[str] = None,
    on_winner=None,
) -> EvalResult:
    """
    Async wrapper. Runs evaluate() in thread pool (non-blocking).
    If result is a winner and on_winner callback provided, calls it.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: evaluate(query, response_text, goal_type,
                         audit_warnings, compliance_result, user_feedback),
    )

    logger.info(
        "eval: score=%.3f winner=%s goal=%s dims=%s",
        result.score, result.is_winner, goal_type,
        {k: f"{v:.2f}" for k, v in result.dimensions.items()},
    )

    if result.is_winner and on_winner is not None:
        try:
            if asyncio.iscoroutinefunction(on_winner):
                await on_winner(result)
            else:
                on_winner(result)
        except Exception as exc:
            logger.warning("on_winner callback failed: %s", exc)

    return result
