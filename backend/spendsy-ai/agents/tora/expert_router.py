"""
Expert router — MoE-inspired prompt routing for Gemma 4.

Instead of switching models, we switch *prompt preambles*. Each "expert"
is a domain-specific instruction block prepended to the system prompt,
giving Gemma 4 focused context for that query type. This mimics the
Mixture-of-Experts pattern from OpenMythos at the prompt level:
one model, multiple specializations activated by routing.

The router runs BEFORE the LLM call and costs zero inference tokens —
it's pure regex + keyword matching on the user's question.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional

# ─── Expert definitions ───

@dataclass(frozen=True)
class Expert:
    expert_id: str
    keywords: re.Pattern
    preamble: str
    priority: int = 0  # higher = stronger match; breaks ties


TAX_EXPERT = Expert(
    expert_id="tax",
    priority=10,
    keywords=re.compile(
        r"\b(?:tax|itr|income\s*tax|80[cCdD]|huf|hra|deduction|regime|"
        r"old\s+regime|new\s+regime|advance\s+tax|tds|gst|capital\s+gain|"
        r"ltcg|stcg|section\s+\d+|cess|surcharge|rebate|exemption|"
        r"80c|80d|nps|elss|fiscal\s+year|fy\s*\d|ay\s*\d)\b",
        re.IGNORECASE,
    ),
    preamble=(
        "[EXPERT MODE: Indian Tax Specialist]\n"
        "You are operating as TORA's tax expert. Apply these rules strictly:\n"
        "- Fiscal year = April–March. FY 2025-26 means 1 Apr 2025 – 31 Mar 2026.\n"
        "- Always compare old vs new regime when recommending deductions.\n"
        "- Cite section numbers (e.g. 80C, 80D, 24b) when mentioning deductions.\n"
        "- Advance tax due dates: 15 Jun (15%), 15 Sep (45%), 15 Dec (75%), 15 Mar (100%).\n"
        "- Never recommend tax evasion. Distinguish avoidance (legal) from evasion.\n"
        "- Use ₹ lakhs/crores notation, not millions/billions.\n"
    ),
)

LOAN_EXPERT = Expert(
    expert_id="loan",
    priority=8,
    keywords=re.compile(
        r"\b(?:loan|emi|mortgage|home\s*loan|car\s*loan|personal\s*loan|"
        r"repay|prepay|refinance|interest\s*rate|amortiz|tenure|"
        r"principal|outstanding|foreclosure|balance\s*transfer)\b",
        re.IGNORECASE,
    ),
    preamble=(
        "[EXPERT MODE: Loan & EMI Specialist]\n"
        "You are operating as TORA's loan expert. Apply these rules:\n"
        "- Always show EMI formula context: EMI = P × r × (1+r)^n / ((1+r)^n - 1).\n"
        "- Compare prepayment benefit (interest saved) vs opportunity cost of investing.\n"
        "- Flag if EMI exceeds 40% of monthly surplus — that's a stress threshold.\n"
        "- For home loans: mention 80C (principal ≤1.5L) and 24b (interest ≤2L) benefits.\n"
        "- Show total interest paid over tenure, not just EMI amount.\n"
    ),
)

INVESTMENT_EXPERT = Expert(
    expert_id="investment",
    priority=8,
    keywords=re.compile(
        r"\b(?:invest|mutual\s*fund|sip|stock|equity|debt\s*fund|"
        r"ppf|fd|fixed\s*deposit|nps|gold|portfolio|asset\s*alloc|"
        r"return|cagr|nav|amc|nifty|sensex|index\s*fund|etf|"
        r"dividend|compound|wealth)\b",
        re.IGNORECASE,
    ),
    preamble=(
        "[EXPERT MODE: Investment Advisor]\n"
        "You are operating as TORA's investment expert. Apply these rules:\n"
        "- Always mention risk level (conservative/moderate/aggressive) for suggestions.\n"
        "- Use CAGR for return comparisons, not absolute returns.\n"
        "- SIP recommendations: show power of compounding with year-wise projections.\n"
        "- Distinguish between equity (volatile, long-term) and debt (stable, short-term).\n"
        "- For FD vs MF comparisons: factor in tax on FD interest vs LTCG on MF.\n"
        "- SEBI disclaimer is mandatory for any specific fund/stock mention.\n"
    ),
)

BUDGET_EXPERT = Expert(
    expert_id="budget",
    priority=5,
    keywords=re.compile(
        r"\b(?:budget|spend|expense|save|saving|cut\s*cost|"
        r"monthly|daily\s*limit|category|overspend|afford|"
        r"surplus|deficit|cash\s*flow|50.30.20|envelope)\b",
        re.IGNORECASE,
    ),
    preamble=(
        "[EXPERT MODE: Budget & Cashflow Analyst]\n"
        "You are operating as TORA's budgeting expert. Apply these rules:\n"
        "- Reference the user's actual monthly income and category-wise spend from context.\n"
        "- Compare spend to national/city benchmarks when available.\n"
        "- Identify top 3 categories for savings potential.\n"
        "- Use daily-limit framing (₹X/day) for actionable advice, not just monthly totals.\n"
        "- Flag recurring subscriptions and suggest consolidation.\n"
    ),
)

PLANNING_EXPERT = Expert(
    expert_id="planning",
    priority=7,
    keywords=re.compile(
        r"\b(?:plan|goal|target|retire|wedding|house|car|trip|"
        r"travel|education|child|emergency\s*fund|save\s*for|"
        r"how\s+long|when\s+can|afford|timeline|roadmap)\b",
        re.IGNORECASE,
    ),
    preamble=(
        "[EXPERT MODE: Financial Planner]\n"
        "You are operating as TORA's financial planning expert. Apply these rules:\n"
        "- Always calculate: required monthly savings = target / months_remaining.\n"
        "- Compare required savings against actual surplus — flag if impossible.\n"
        "- Suggest phased approaches if goal exceeds current capacity.\n"
        "- Factor inflation (6-7% India avg) into future cost projections.\n"
        "- Use the user's existing plans/goals from context to avoid contradictions.\n"
    ),
)

# Registry ordered by priority (highest first)
_EXPERTS: List[Expert] = sorted(
    [TAX_EXPERT, LOAN_EXPERT, INVESTMENT_EXPERT, BUDGET_EXPERT, PLANNING_EXPERT],
    key=lambda e: e.priority,
    reverse=True,
)


def route_to_expert(question: str) -> Optional[Expert]:
    """Match question to best expert. Returns None for general queries."""
    if not question:
        return None

    matches = []
    for expert in _EXPERTS:
        hits = expert.keywords.findall(question)
        if hits:
            matches.append((expert, len(hits), expert.priority))

    if not matches:
        return None

    # Sort by (hit_count * priority) descending — most relevant expert wins
    matches.sort(key=lambda m: m[1] * m[2], reverse=True)
    return matches[0][0]


def inject_expert_preamble(system_prompt: str, question: str) -> tuple[str, str | None]:
    """Route question → expert, prepend preamble to system prompt.

    Returns (augmented_system_prompt, expert_id_or_none).
    """
    expert = route_to_expert(question)
    if expert is None:
        return system_prompt, None
    return expert.preamble + "\n" + system_prompt, expert.expert_id
