"""
Render FetchResult tuples into a prose block the LLM can consume.

Design principle: gemma4:e2b parses structured prose much better than
nested JSON. Every fact becomes a short line of text. Token budgets are
enforced per-plugin; primary plugin gets its full budget, supporting
plugin is capped at 30% of combined budget.

Output shape (injected just before the user's QUESTION line in the prompt):

  === REAL-TIME DATA: GOLD (primary) ===
  Spot gold (22K): ₹70,800 per 10g (IBJA daily rate, high confidence).
  Making charges at branded jewellers: 8-18% range.
  GST on jewellery: 3%.
  Sovereign Gold Bond: 2.5% annual interest, 8-year tenure, zero capital gain tax on maturity.
  Rules to apply:
    • For pure investment intent, prefer SGB > Gold ETF > Digital Gold > Physical gold.
    • Making charges on jewellery are non-recoverable on resale.

  Prices indicative, based on recent published rates (April 2026 for some categories).
"""

from __future__ import annotations

import logging
from typing import Any

from .fetch_registry import (
    FetchResult,
    FetchStrategy,
    PLUGIN_REGISTRY,
    PluginMatch,
    confidence_label,
)

logger = logging.getLogger(__name__)

# Rough char-to-token ratio for gemma tokenizer on English + numbers.
# Deliberately conservative (4.5 chars/token vs the usual 4) — we'd rather
# render fewer tokens than the budget than blow through it.
_CHARS_PER_TOKEN = 4.5

SUPPORTING_BUDGET_FRACTION = 0.3  # secondary plugin gets <=30% of combined budget


def build_market_context_block(
    results: list[tuple[PluginMatch, FetchResult]],
    max_total_tokens: int | None = None,
) -> str:
    """Render resolved fetcher output into an injectable prompt block.

    Returns "" when `results` is empty — caller should omit the header
    entirely rather than inject an empty block (wastes tokens and
    confuses the model).
    """
    if not results:
        return ""

    # Split primary vs supporting; compute per-plugin token ceilings.
    primary_budget = 0
    supporting_budget = 0
    for match, _ in results:
        plugin = PLUGIN_REGISTRY.get(match.plugin_id)
        if plugin is None:
            continue
        if match.role == "primary":
            primary_budget = plugin.token_budget
        else:
            supporting_budget = int(plugin.token_budget * SUPPORTING_BUDGET_FRACTION)

    combined_budget = primary_budget + supporting_budget
    if max_total_tokens is not None:
        combined_budget = min(combined_budget, max_total_tokens)

    sections: list[str] = []
    any_fallback_used = False
    fallback_sources: list[str] = []

    for match, result in results:
        plugin = PLUGIN_REGISTRY.get(match.plugin_id)
        if plugin is None:
            continue
        per_plugin_budget = (
            primary_budget if match.role == "primary" else supporting_budget
        )
        if per_plugin_budget <= 0:
            continue
        section = _render_section(match, result, plugin.priority_keys, per_plugin_budget)
        if section:
            sections.append(section)

        # Provenance bookkeeping for the footer.
        strategy = result.provenance.get("strategy")
        if strategy in (
            FetchStrategy.CURATED_STATIC.value,
            FetchStrategy.ESTIMATED.value,
            FetchStrategy.CACHED_QUARTERLY.value,
        ):
            any_fallback_used = True
        if not result.provenance.get("any_live_used"):
            any_fallback_used = True
        src = result.provenance.get("fallback_source")
        if src and src not in fallback_sources:
            fallback_sources.append(src)

    if not sections:
        return ""

    block = "\n\n".join(sections)
    footer = _build_footer(any_fallback_used, fallback_sources)
    if footer:
        block = block + "\n\n" + footer
    return block


def _render_section(
    match: PluginMatch,
    result: FetchResult,
    priority_keys: list[str],
    token_budget: int,
) -> str:
    """Render one plugin's facts + constraints into a prose section."""
    role_tag = match.role.upper()
    title = f"=== {match.plugin_id.replace('_', ' ').upper()} ({role_tag}) ==="

    facts_lines: list[str] = []

    # Render priority keys first, in declared order.
    ordered_keys = list(priority_keys) + [
        k for k in result.facts.keys() if k not in priority_keys
    ]
    for key in ordered_keys:
        fact = result.facts.get(key)
        if fact is None:
            continue
        line = _render_fact_line(key, fact)
        if line:
            facts_lines.append(line)

    constraints_lines: list[str] = []
    if result.constraints:
        constraints_lines.append("Rules to apply:")
        for rule in result.constraints:
            constraints_lines.append(f"  • {rule}")

    # Assemble under budget. Facts first, then constraints — constraints
    # are behavioural guardrails and matter even if we run short of tokens
    # on pure data, so we keep a reserve for them.
    budget_chars = int(token_budget * _CHARS_PER_TOKEN)
    reserve_for_constraints = min(400, int(budget_chars * 0.35)) if constraints_lines else 0
    facts_budget = budget_chars - reserve_for_constraints

    rendered_facts: list[str] = []
    used = 0
    for line in facts_lines:
        if used + len(line) + 1 > facts_budget:
            rendered_facts.append("  (additional details trimmed to fit context)")
            break
        rendered_facts.append(line)
        used += len(line) + 1

    rendered_constraints: list[str] = []
    used_c = 0
    for line in constraints_lines:
        if used_c + len(line) + 1 > reserve_for_constraints:
            break
        rendered_constraints.append(line)
        used_c += len(line) + 1

    parts = [title]
    parts.extend(rendered_facts)
    if rendered_constraints:
        parts.append("")  # spacer
        parts.extend(rendered_constraints)
    return "\n".join(parts)


def _render_fact_line(key: str, fact: dict[str, Any]) -> str:
    """Turn one fact dict into a single sentence.

    Facts with range/dict values are flattened into inline descriptions
    so the LLM doesn't see raw JSON braces."""
    value = fact.get("value")
    confidence = fact.get("confidence")
    source = fact.get("source", "")

    label = key.replace("_", " ").replace("inr", "₹").strip()
    rendered_value = _render_value(value, key_hint=key)
    if not rendered_value:
        return ""

    # Confidence tag — only surface when medium/low so the LLM knows to hedge.
    # High-confidence facts get no tag; they're just quoted plainly.
    conf_tag = ""
    if isinstance(confidence, (int, float)):
        label_text = confidence_label(float(confidence))
        if label_text != "high":
            conf_tag = f" [{label_text} confidence]"

    return f"- {label}: {rendered_value}{conf_tag}"


def _render_value(value: Any, key_hint: str = "") -> str:
    """Recursive-ish renderer for fact values.

    Scalars → as-is. Dicts with min/max → "₹X–₹Y" (or "X%–Y%" if the key
    hint indicates a percentage). Other dicts → inline "key=value" pairs,
    capped at 4 entries for brevity. Lists → "[A, B, C]".

    `key_hint` lets the renderer pick the right unit for the fact —
    if the key contains "pct" or "percent" or "rate", values render as
    percentages so the number auditor sees them in the expected form.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"

    is_pct = _is_pct_key(key_hint)

    if isinstance(value, (int, float)):
        if is_pct:
            return f"{value}%"
        return f"₹{value:,.0f}" if value >= 1000 else f"{value}"
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        if set(value.keys()) == {"min", "max"}:
            if is_pct:
                return f"{value['min']}%–{value['max']}%"
            return f"₹{value['min']:,.0f}–₹{value['max']:,.0f}"
        # Child hint inherits the outer hint when the outer key is a pct
        # key (e.g. gst_pct: {jewellery: 3, making_charges: 5}). This
        # ensures the auditor sees "3%" not "3" in the context.
        if len(value) <= 4:
            parts = []
            for k, v in value.items():
                child_hint = k if not is_pct else f"{key_hint}__{k}"
                rendered = _render_value(v, key_hint=child_hint)
                parts.append(f"{k.replace('_', ' ')}: {rendered}")
            return "; ".join(parts)
        first_three = list(value.items())[:3]
        parts = []
        for k, v in first_three:
            child_hint = k if not is_pct else f"{key_hint}__{k}"
            rendered = _render_value(v, key_hint=child_hint)
            parts.append(f"{k.replace('_', ' ')}: {rendered}")
        return "; ".join(parts) + f" (+{len(value) - 3} more)"
    if isinstance(value, list):
        if not value:
            return ""
        rendered_items = [_render_value(v, key_hint=key_hint) for v in value[:5]]
        return ", ".join(r for r in rendered_items if r)
    return str(value)


def _is_pct_key(key: str) -> bool:
    """Heuristic: is this field a percentage?

    Matches "pct", "percent", "rate", "interest", "discount", "markup",
    "yield", "cagr", "return". Conservative — false negatives are fine
    (fact renders as a rupee, auditor sees a rupee); false positives are
    the problem (renders "₹70,800%" which is wrong).
    """
    if not key:
        return False
    k = key.lower()
    pct_markers = (
        "pct", "percent", "rate_pct", "_rate", "interest",
        "discount", "markup", "yield", "cagr", "returns", "return_pct",
    )
    # Avoid false positive on things like "per_10g" or "per_kg" which
    # aren't percentages. Require explicit pct/percent/rate markers.
    return any(m in k for m in pct_markers)


def _build_footer(any_fallback_used: bool, fallback_sources: list[str]) -> str:
    """Subtle single-line footer acknowledging curated-static data when used.

    We deliberately do NOT print loud warnings — that would make the LLM
    over-hedge. The user sees a quiet note; the LLM sees a factual tag.
    """
    if not any_fallback_used:
        return ""
    return (
        "Prices indicative, based on recent published rates. "
        "Tell the user this only if they ask about freshness."
    )
