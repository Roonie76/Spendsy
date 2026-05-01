"""
Goal Decomposer — Phase 3.

Extracts a structured GoalStruct from a natural-language query + user profile.
Called BEFORE the LLM so the reasoner has typed inputs to work with.

Output: GoalStruct dataclass with:
  goal_type     — enum: CAR / HOUSE / WEDDING / TRAVEL / EDUCATION /
                         RETIREMENT / LOAN_REPAY / INVEST / EMERGENCY / GENERIC
  target_amount — float INR (None if not stated)
  timeline_months — int (None if not stated)
  constraints   — list of hard constraints extracted from query
  raw_entities  — dict of detected entities (model, city, rate, etc.)

Detection strategy:
  1. goal_type   — keyword regex over query
  2. amount      — ₹/lakh/crore patterns
  3. timeline    — year/month/week patterns
  4. constraints — "under X", "max X EMI", "within N months", budget caps

No LLM call — pure deterministic extraction. Fast, zero-cost, always runs.
Falls back gracefully: unknown fields stay None, goal_type = GENERIC.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class GoalType(str, Enum):
    CAR         = "car"
    HOUSE       = "house"
    WEDDING     = "wedding"
    TRAVEL      = "travel"
    EDUCATION   = "education"
    RETIREMENT  = "retirement"
    LOAN_REPAY  = "loan_repay"
    INVEST      = "invest"
    EMERGENCY   = "emergency"
    GENERIC     = "generic"


@dataclass
class GoalStruct:
    goal_type: GoalType = GoalType.GENERIC
    target_amount: Optional[float] = None
    timeline_months: Optional[int] = None
    constraints: list[str] = field(default_factory=list)
    raw_entities: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        parts = [f"Goal: {self.goal_type.value}"]
        if self.target_amount:
            parts.append(f"Target: ₹{self.target_amount:,.0f}")
        if self.timeline_months:
            parts.append(f"Timeline: {self.timeline_months}m")
        if self.constraints:
            parts.append("Constraints: " + "; ".join(self.constraints))
        return " | ".join(parts)


# ── Goal type patterns ────────────────────────────────────────────────────────

_GOAL_PATTERNS: list[tuple[GoalType, re.Pattern]] = [
    # English patterns
    (GoalType.CAR,        re.compile(r"\b(car|bike|ev|scooter|vehicle|auto\s*loan|two.?wheel|swift|nexon|activa|splendor|on.road)\b", re.I)),
    (GoalType.HOUSE,      re.compile(r"\b(house|home|flat|apartment|property|real\s*estate|home\s*loan|plot|ghar\s*lena|makaan)\b", re.I)),
    (GoalType.WEDDING,    re.compile(r"\b(wedding|marriage|shaadi|nikah|reception|engagement|barat|vivah)\b", re.I)),
    (GoalType.TRAVEL,     re.compile(r"\b(travel|trip|vacation|holiday|tour|international|flight|europe|usa|dubai|goa|manali|thailand|japan|bali|singapore)\b", re.I)),
    (GoalType.EDUCATION,  re.compile(r"\b(education|college|university|mba|course|fees|tuition|study\s*abroad|padhai|sukanya)\b", re.I)),
    (GoalType.RETIREMENT, re.compile(r"\b(retire|retirement|pension|nps|corpus|post.?retirement|fire|retire\s*karna)\b", re.I)),
    (GoalType.LOAN_REPAY, re.compile(r"\b(repay|pay.?off|clear\s*(loan|debt|card|emi)|foreclose|prepay|close\s*loan|cibil|credit\s*score\s*sudhaar)\b", re.I)),
    (GoalType.INVEST,     re.compile(r"\b(invest|sip|mutual\s*fund|stock|equity|ppf|elss|fd|fixed\s*deposit|gold|portfolio|regime|80c|tax\s*sav|bachaana)\b", re.I)),
    (GoalType.EMERGENCY,  re.compile(r"\b(emergency\s*fund|rainy\s*day|safety\s*net|3\s*months?\s*expense|6\s*months?\s*expense|insurance|operation|surgery|medical)\b", re.I)),
    # Hinglish-specific patterns (romanised Hindi mixed with English)
    (GoalType.CAR,        re.compile(r"\b(gaadi|bike\s*lena|car\s*lena|scooter\s*lena|vehicle\s*lena)\b", re.I)),
    (GoalType.HOUSE,      re.compile(r"\b(flat\s*lena|ghar\s*kharidna|property\s*lena|makaan\s*lena)\b", re.I)),
    (GoalType.TRAVEL,     re.compile(r"\b(trip\s*(plan|kar)|jaana\s*hai|vacation\s*plan|ghoomna)\b", re.I)),
    (GoalType.INVEST,     re.compile(r"\b(invest\s*karna|paisa\s*lagana|tax\s*bachana|regime\s*(select|choose|better))\b", re.I)),
    (GoalType.LOAN_REPAY, re.compile(r"\b(cibil\s*(score|sudhaar|improve)|loan\s*(chukana|band|clear)|emi\s*(miss|default))\b", re.I)),
    (GoalType.EMERGENCY,  re.compile(r"\b(insurance\s*(lena|kharidna)|operation\s*(hua|ka|ke)|health\s*(plan|policy))\b", re.I)),
    (GoalType.RETIREMENT, re.compile(r"\b(retire\s*(karna|hona|chahta)|pension\s*(plan|chahiye)|corpus\s*(banana|chahiye))\b", re.I)),
]

# ── Amount patterns ───────────────────────────────────────────────────────────

_CRORE_RE  = re.compile(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:crore|cr)\b", re.I)
_LAKH_RE   = re.compile(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakhs?|lacs?|l)\b", re.I)
_RUPEE_RE  = re.compile(r"(?:₹|rs\.?|inr)\s*([0-9,]+(?:\.[0-9]+)?)\b", re.I)


def _extract_amount(text: str) -> Optional[float]:
    m = _CRORE_RE.search(text)
    if m:
        return float(m.group(1)) * 1_00_00_000
    m = _LAKH_RE.search(text)
    if m:
        return float(m.group(1)) * 1_00_000
    m = _RUPEE_RE.search(text)
    if m:
        raw = float(m.group(1).replace(",", ""))
        return raw if raw >= 1000 else None   # ignore tiny amounts
    return None


# ── Timeline patterns ─────────────────────────────────────────────────────────

_YEAR_RE   = re.compile(r"(\d+(?:\.\d+)?)\s*year", re.I)
_MONTH_RE  = re.compile(r"(\d+)\s*month", re.I)
_WEEK_RE   = re.compile(r"(\d+)\s*week", re.I)


def _extract_timeline_months(text: str) -> Optional[int]:
    m = _YEAR_RE.search(text)
    if m:
        return max(1, round(float(m.group(1)) * 12))
    m = _MONTH_RE.search(text)
    if m:
        return max(1, int(m.group(1)))
    m = _WEEK_RE.search(text)
    if m:
        return max(1, round(int(m.group(1)) / 4.33))
    return None


# ── Constraint patterns ───────────────────────────────────────────────────────

_CONSTRAINT_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("max_emi",     re.compile(r"(?:emi|payment)\s*(?:under|below|max|upto|up\s*to)\s*(?:₹|rs\.?)?\s*([0-9,]+)", re.I)),
    ("budget_cap",  re.compile(r"budget\s*(?:of|is|:)?\s*(?:₹|rs\.?)?\s*([0-9,]+)", re.I)),
    ("no_loan",     re.compile(r"\b(no\s*loan|without\s*loan|avoid\s*(loan|debt)|cash\s*purchase|full\s*payment)\b", re.I)),
    ("low_risk",    re.compile(r"\b(low\s*risk|safe|conservative|capital\s*protection|guaranteed)\b", re.I)),
    ("high_return", re.compile(r"\b(high\s*return|maximum\s*return|aggressive|best\s*return)\b", re.I)),
    ("tax_saving",  re.compile(r"\b(tax\s*sav|80c|80d|tax\s*benefit|tax\s*efficient)\b", re.I)),
]


def _extract_constraints(text: str) -> tuple[list[str], dict[str, Any]]:
    constraints = []
    entities: dict[str, Any] = {}
    for name, pat in _CONSTRAINT_PATTERNS:
        m = pat.search(text)
        if m:
            if m.lastindex and m.lastindex >= 1:
                try:
                    val = float(m.group(1).replace(",", ""))
                    entities[name] = val
                    if name == "max_emi":
                        constraints.append(f"EMI must not exceed ₹{val:,.0f}/month")
                    elif name == "budget_cap":
                        constraints.append(f"Total budget capped at ₹{val:,.0f}")
                except ValueError:
                    pass
            else:
                entities[name] = True
                if name == "no_loan":
                    constraints.append("User prefers no loan / cash purchase")
                elif name == "low_risk":
                    constraints.append("Risk appetite: low / conservative")
                elif name == "high_return":
                    constraints.append("Preference: maximize returns (higher risk acceptable)")
                elif name == "tax_saving":
                    constraints.append("Tax-saving options preferred")
    return constraints, entities


# ── City / model entity extraction ───────────────────────────────────────────

_CITY_LIST = [
    "delhi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai",
    "kolkata", "pune", "ahmedabad", "jaipur", "lucknow", "chandigarh",
    "noida", "gurugram", "gurgaon", "kochi", "indore", "bhopal", "surat",
]

def _extract_city(text: str) -> Optional[str]:
    tl = text.lower()
    for city in _CITY_LIST:
        if city in tl:
            return city
    return None


# ── Main decomposer ───────────────────────────────────────────────────────────

def decompose_goal(
    query: str,
    user_profile: Optional[dict[str, Any]] = None,
) -> GoalStruct:
    """
    Extract structured GoalStruct from query + optional user profile.

    Args:
        query:        Natural-language user query.
        user_profile: Dict with keys {city, surplus, income, tier}.

    Returns:
        GoalStruct — always returns, never raises.
    """
    if not query:
        return GoalStruct()

    # 1. Goal type
    goal_type = GoalType.GENERIC
    best_hits = 0
    for gtype, pat in _GOAL_PATTERNS:
        hits = len(pat.findall(query))
        if hits > best_hits:
            best_hits = hits
            goal_type = gtype

    # 2. Amount
    target_amount = _extract_amount(query)

    # 3. Timeline
    timeline_months = _extract_timeline_months(query)

    # 4. Constraints + raw entities
    constraints, entities = _extract_constraints(query)

    # 5. City from query or profile
    city = _extract_city(query) or (user_profile or {}).get("city", "")
    if city:
        entities["city"] = city

    # 6. Enrich entities with profile context
    if user_profile:
        if user_profile.get("surplus"):
            entities["monthly_surplus"] = float(user_profile["surplus"])
        if user_profile.get("income"):
            entities["annual_income"] = float(user_profile["income"])

    # 7. Derive implicit constraints from profile
    surplus = entities.get("monthly_surplus", 0)
    if surplus > 0 and target_amount and timeline_months:
        required_monthly = target_amount / timeline_months
        if required_monthly > surplus * 0.80:
            constraints.append(
                f"Warning: required monthly saving ₹{required_monthly:,.0f} "
                f"exceeds 80% of surplus ₹{surplus:,.0f} — goal may be aggressive"
            )

    return GoalStruct(
        goal_type=goal_type,
        target_amount=target_amount,
        timeline_months=timeline_months,
        constraints=constraints,
        raw_entities=entities,
    )
