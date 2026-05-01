"""
Few-Shot Injector — Phase 4 AI trainer loop.

At prompt-build time, retrieves top-3 similar winning traces from reasoning_store
by embedding similarity, then injects them as few-shot examples into the
TORA system prompt.

Replaces static examples in tora_personality.py with dynamic, query-relevant
examples that improve with every winning trace stored.

Similarity: cosine over embed_text() from Phase 2 RAG vector_store.
Falls back gracefully (returns empty string) if no traces available.

Token budget: max 600 chars per example × 3 = ~1800 chars total.
Injected as a block at the END of the system prompt (recency-biased).
"""
from __future__ import annotations

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

MAX_EXAMPLES   = 3
MAX_CHARS_EACH = 600
MIN_SIMILARITY = 0.30   # don't inject irrelevant examples


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na  = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb  = math.sqrt(sum(x * x for x in b)) or 1e-9
    return dot / (na * nb)


def _embed(text: str) -> list[float]:
    """Embed via RAG vector_store (Gemini or hash fallback)."""
    try:
        from agents.tora.rag.vector_store import embed_text
        return embed_text(text)
    except Exception:
        # Ultra-minimal fallback: zero vector (similarity = 0, no injection)
        return [0.0] * 768


def _format_example(trace: dict, rank: int) -> str:
    """Format a single trace as a few-shot example block."""
    query      = trace.get("query", "")[:200]
    best       = trace.get("best_strategy", {})
    response   = trace.get("response", "")[:MAX_CHARS_EACH]
    score      = trace.get("eval_score", 0)
    goal       = trace.get("goal_type", "generic")
    techniques = trace.get("technique_tag", [])
    why        = trace.get("why_it_matters", "")
    chain      = trace.get("reasoning_chain", "")

    tech_str = f" [{', '.join(techniques)}]" if techniques else ""
    lines = [
        f"[Example {rank} — {goal}{tech_str} | score {score:.2f}]",
        f"Q: {query}",
    ]
    if chain:
        lines.append(f"Reasoning: {chain[:300]}")
    if best:
        lines.append(
            f"Best strategy: {best.get('name','')} | "
            f"Monthly ₹{best.get('monthly_outflow_inr', best.get('monthly_outflow', 0)) or 0:,} | "
            f"Total ₹{best.get('total_cost_inr', best.get('total_cost', 0)) or 0:,}"
        )
    lines.append(f"A: {response}")
    if why:
        lines.append(f"Why: {why}")
    return "\n".join(lines)


def inject_few_shots(
    system_prompt: str,
    query: str,
    goal_type: str = "generic",
    n_examples: int = MAX_EXAMPLES,
) -> str:
    """
    Retrieve similar winning traces and prepend them as few-shot examples
    at the end of the system prompt.

    Args:
        system_prompt: Current TORA system prompt string.
        query:         Current user query.
        goal_type:     Detected goal type (for targeted retrieval).
        n_examples:    Max examples to inject.

    Returns:
        Augmented system prompt (or original if no examples found).
    """
    try:
        from fine_tuning.reasoning_store import load_traces
    except ImportError:
        return system_prompt

    # Load candidates — same goal type first, then generic fallback
    candidates = load_traces(goal_type, limit=50, min_score=0.75)
    if not candidates and goal_type != "generic":
        candidates = load_traces("generic", limit=20, min_score=0.75)

    if not candidates:
        return system_prompt   # no traces yet — no injection

    # Detect techniques for this query to boost matching traces
    try:
        from agents.tora.reasoning.techniques import tag_techniques
        current_techniques = set(tag_techniques(query))
    except Exception:
        current_techniques = set()

    # Embed query and score candidates by similarity + technique overlap
    q_emb = _embed(query)
    scored = []
    for trace in candidates:
        t_emb = _embed(trace.get("query", ""))
        sim   = _cosine(q_emb, t_emb)
        # Boost by technique overlap (up to +0.10)
        trace_techs = set(trace.get("technique_tag", []))
        overlap = len(current_techniques & trace_techs)
        technique_boost = min(overlap * 0.05, 0.10)
        adjusted_sim = sim + technique_boost
        if adjusted_sim >= MIN_SIMILARITY:
            scored.append((adjusted_sim, trace))

    if not scored:
        return system_prompt

    scored.sort(key=lambda x: -x[0])
    top = scored[:n_examples]

    examples_block = "\n\n## Few-Shot Examples (high-quality past responses — follow this style)\n"
    for rank, (sim, trace) in enumerate(top, 1):
        examples_block += "\n" + _format_example(trace, rank) + "\n"
    examples_block += "\n[End of examples — now answer the current question]\n"

    logger.info(
        "few_shot_injector: injected %d examples for goal=%s (top sim=%.3f)",
        len(top), goal_type, top[0][0],
    )

    return system_prompt + examples_block
