"""
Reasoning Techniques — Phase 5.

Six first-principles thinking modes TORA applies when decomposing goals.
Each technique shapes HOW TORA frames the problem, not just what answer it gives.

Techniques (from the training spec):
  1. first_principles  — strip assumptions, find what the user actually needs
  2. second_order      — think 2 moves ahead (what happens AFTER this plan?)
  3. inversion         — ask "what would make this impossible?" then remove blockers
  4. analogical        — borrow frameworks from other fields (engineering, ecology)
  5. constraint_relax  — remove one rule at a time, open solution branches
  6. reframing         — change the question itself, not just the answer

Each technique has:
  - id:          snake_case identifier (stored in traces)
  - name:        display name
  - prompt_hint: 1-2 sentence injection into TORA's system prompt
  - trigger_fn:  callable(query, goal_struct) -> bool — when to auto-apply
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class Technique:
    id: str
    name: str
    prompt_hint: str
    trigger_fn: Callable[..., bool]


# ---------------------------------------------------------------------------
# Trigger helpers
# ---------------------------------------------------------------------------

def _has_any(query: str, *patterns: str) -> bool:
    q = query.lower()
    return any(re.search(p, q) for p in patterns)


def _goal_type_is(goal_struct: Optional[dict], *types: str) -> bool:
    if not goal_struct:
        return False
    return goal_struct.get("goal_type", "").lower() in types


# ---------------------------------------------------------------------------
# The six techniques
# ---------------------------------------------------------------------------

TECHNIQUES: list[Technique] = [

    Technique(
        id="first_principles",
        name="First Principles",
        prompt_hint=(
            "Strip away surface assumptions. Ask: what is the user actually trying to achieve? "
            "Not 'buy a car' — but 'reliable transport under ₹X/month'. "
            "Restate the goal at its atomic level before proposing any solution."
        ),
        trigger_fn=lambda q, gs=None: _has_any(
            q,
            r"\bwant\s+to\s+buy\b", r"\bshould\s+i\b", r"\bbest\s+way\b",
            r"\badvice\b", r"\bhelp\s+me\b",
        ),
    ),

    Technique(
        id="second_order",
        name="Second Order",
        prompt_hint=(
            "Think two moves ahead. After this plan executes — what changes? "
            "Paying off a card frees cash-flow which then unlocks a better loan rate. "
            "Always model the knock-on effect, not just the immediate outcome."
        ),
        trigger_fn=lambda q, gs=None: _has_any(
            q,
            r"\bpay\s*off\b", r"\brepay\b", r"\bclose\s+(the\s+)?loan\b",
            r"\bemi\b", r"\bforeclose\b", r"\bsettle\b",
        ),
    ),

    Technique(
        id="inversion",
        name="Inversion",
        prompt_hint=(
            "Instead of 'how do I achieve X?', ask 'what would make X impossible?' "
            "then remove each blocker one by one. "
            "List the 3 most likely failure modes before recommending the plan."
        ),
        trigger_fn=lambda q, gs=None: _has_any(
            q,
            r"\bcan\s+i\s+afford\b", r"\bwill\s+i\s+qualify\b",
            r"\bfeasible\b", r"\bpossible\b", r"\bworry\b", r"\brisk\b",
        ),
    ),

    Technique(
        id="analogical",
        name="Analogical",
        prompt_hint=(
            "Borrow frameworks from other fields. "
            "Debt consolidation is like load balancing in engineering. "
            "Portfolio rebalancing is like species diversification in ecology. "
            "Use the analogy to make the recommendation vivid and intuitive."
        ),
        trigger_fn=lambda q, gs=None: _has_any(
            q,
            r"\bportfolio\b", r"\bdiversif\b", r"\brebalanc\b",
            r"\bconsolidat\b", r"\bspread\b",
        ),
    ),

    Technique(
        id="constraint_relax",
        name="Constraint Relax",
        prompt_hint=(
            "Remove one constraint at a time and explore whether the problem dissolves. "
            "What if the credit score wasn't the bottleneck? What if the car was leased not bought? "
            "Each relaxation opens a new solution branch — list at least two."
        ),
        trigger_fn=lambda q, gs=None: _has_any(
            q,
            r"\bcan't\b", r"\bcannot\b", r"\bdon't\s+have\b", r"\bno\s+savings\b",
            r"\blow\s+cibil\b", r"\bbad\s+credit\b", r"\bnot\s+eligible\b",
            r"\brejected\b",
        ),
    ),

    Technique(
        id="reframing",
        name="Reframing",
        prompt_hint=(
            "Change the question itself, not just the answer. "
            "User asks 'best EMI for a car' — reframe as 'cheapest total cost of mobility': "
            "public transport + occasional rental may win. "
            "Always present the reframed version alongside the literal answer."
        ),
        trigger_fn=lambda q, gs=None: (
            _has_any(q, r"\bbest\b", r"\bcheapest\b", r"\blowest\b", r"\boptimal\b")
            and _has_any(q, r"\bemi\b", r"\bloan\b", r"\bcar\b", r"\bhouse\b")
        ),
    ),
]

# Fast lookup by id
TECHNIQUE_MAP: dict[str, Technique] = {t.id: t for t in TECHNIQUES}


# ---------------------------------------------------------------------------
# Auto-tagger
# ---------------------------------------------------------------------------

def tag_techniques(
    query: str,
    goal_struct: Optional[dict] = None,
    max_tags: int = 2,
) -> list[str]:
    """
    Return up to max_tags technique IDs that should be applied to this query.
    Priority: order in TECHNIQUES list (first_principles first).
    """
    tags: list[str] = []
    for tech in TECHNIQUES:
        if len(tags) >= max_tags:
            break
        try:
            if tech.trigger_fn(query, goal_struct):
                tags.append(tech.id)
        except Exception:
            continue
    return tags


def build_technique_block(technique_ids: list[str]) -> str:
    """
    Build the prompt block injected into TORA's system prompt.
    Called by tora_agent with the tags returned by tag_techniques().
    """
    if not technique_ids:
        return ""
    lines = ["=== REASONING TECHNIQUES ==="]
    for tid in technique_ids:
        tech = TECHNIQUE_MAP.get(tid)
        if tech:
            lines.append(f"[{tech.name.upper()}] {tech.prompt_hint}")
    lines.append("Apply the above technique(s) explicitly in your reasoning.")
    return "\n".join(lines)
