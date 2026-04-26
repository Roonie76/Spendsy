"""
Context compressor — MLA-inspired token reduction for Gemma 4.

OpenMythos uses Multi-Latent Attention (MLA) to compress KV cache at the
model level. We can't change Gemma's attention, but we CAN compress the
*input context* before it enters the model — achieving similar token
savings at the prompt engineering level.

Three compression strategies, applied in order:
1. Transaction dedup — merge identical-category transactions into aggregates
2. JSON compaction — strip whitespace, shorten keys, remove nulls from extras
3. History compression — summarize old turns into single-line recaps

Combined savings: ~35-50% fewer tokens in the user_message block.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List


# ─── 1. Transaction compression ───

def compress_transactions(transactions: List[Dict[str, Any]], max_items: int = 15) -> str:
    """Compress transaction list into a dense block.

    Instead of 15 individual lines, group by category and show:
    - Top 5 categories with totals
    - Only name individual transactions if they're large outliers (>3x median)
    """
    if not transactions:
        return ""

    # Aggregate by category
    cat_totals: Dict[str, float] = {}
    cat_counts: Dict[str, int] = {}
    all_amounts: List[float] = []
    outliers: List[Dict[str, Any]] = []

    for tx in transactions[:max_items]:
        cat = tx.get("category", "other")
        amt = float(tx.get("amount", 0))
        cat_totals[cat] = cat_totals.get(cat, 0) + amt
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        all_amounts.append(amt)

    # Find outliers (>3x median)
    if all_amounts:
        sorted_amts = sorted(all_amounts)
        median = sorted_amts[len(sorted_amts) // 2]
        threshold = median * 3 if median > 0 else float("inf")

        for tx in transactions[:max_items]:
            amt = float(tx.get("amount", 0))
            if amt > threshold:
                outliers.append(tx)

    # Build compressed block
    lines = []
    top_cats = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)[:6]
    for cat, total in top_cats:
        count = cat_counts[cat]
        lines.append(f"{cat}: ₹{total:,.0f} ({count} txns)")

    result = "=== RECENT ACTIVITY (compressed) ===\n"
    result += " | ".join(lines) + "\n"

    if outliers:
        result += "Notable: "
        result += ", ".join(
            f"{tx.get('title', '?')} {'+'if tx.get('type')=='income' else '-'}₹{float(tx.get('amount',0)):,.0f}"
            for tx in outliers[:3]
        )
        result += "\n"

    return result


# ─── 2. JSON compaction ───

def compact_extras(extras: Dict[str, Any]) -> str:
    """Compress plans/loans/goals/cards JSON to minimal representation.

    Strips null values, shortens keys, removes empty arrays,
    and uses single-line JSON instead of indented.
    """
    if not extras:
        return ""

    # Key shortening map
    _KEY_MAP = {
        "monthly_amount": "mo_amt",
        "target_amount": "target",
        "current_amount": "current",
        "interest_rate": "rate",
        "remaining_tenure": "rem_tenure",
        "outstanding_balance": "balance",
        "credit_limit": "limit",
        "minimum_payment": "min_pay",
        "due_date": "due",
        "created_at": None,  # strip entirely
        "updated_at": None,
        "description": "desc",
        "plan_name": "name",
        "goal_name": "name",
    }

    def _compact_obj(obj: Any) -> Any:
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                mapped = _KEY_MAP.get(k, k)
                if mapped is None:
                    continue  # strip this key
                compacted = _compact_obj(v)
                if compacted is not None and compacted != "" and compacted != []:
                    result[mapped] = compacted
            return result if result else None
        elif isinstance(obj, list):
            items = [_compact_obj(i) for i in obj if _compact_obj(i) is not None]
            return items if items else None
        elif obj is None or obj == "":
            return None
        return obj

    compacted = _compact_obj(extras)
    if not compacted:
        return ""

    # Single-line JSON, no indent
    return "CONTEXT: " + json.dumps(compacted, separators=(",", ":"), default=str) + "\n"


# ─── 3. Conversation history compression ───

def compress_history(history: List[Dict[str, Any]], keep_recent: int = 3) -> str:
    """Compress conversation history.

    Keep last `keep_recent` turns verbatim (they're most relevant for
    follow-ups). Compress older turns into single-line summaries.
    """
    if not history:
        return ""

    valid = [m for m in history if str(m.get("content", "")).strip() and str(m.get("content", "")).strip() != "{}"]
    if not valid:
        return ""

    result = "=== CONVERSATION CONTEXT ===\n"

    if len(valid) <= keep_recent:
        # Few enough to keep all verbatim
        for msg in valid:
            role = msg.get("role", "user").upper()
            content = str(msg.get("content", ""))
            if len(content) > 300:
                content = content[:300] + "…"
            result += f"{role}: {content}\n"
        return result + "\n"

    # Compress older turns
    older = valid[:-keep_recent]
    recent = valid[-keep_recent:]

    # Summarize older turns as topic mentions
    topics = set()
    for msg in older:
        content = str(msg.get("content", "")).lower()
        # Extract key financial terms mentioned
        for term in re.findall(
            r"\b(?:tax|loan|emi|invest|sip|budget|goal|plan|save|spend|"
            r"salary|rent|insurance|fd|ppf|nps|mutual fund|stock)\b",
            content,
        ):
            topics.add(term)

    if topics:
        result += f"[Earlier: discussed {', '.join(sorted(topics)[:8])}]\n"

    # Recent turns verbatim but capped
    for msg in recent:
        role = msg.get("role", "user").upper()
        content = str(msg.get("content", ""))
        if len(content) > 400:
            content = content[:400] + "…"
        result += f"{role}: {content}\n"

    return result + "\n"


# ─── 4. Trend compression ───

def compress_trends(trend_block: str) -> str:
    """Compress verbose trend descriptions into dense deltas.

    Input might be multi-line prose; output is single-line summary.
    """
    if not trend_block or len(trend_block) < 50:
        return trend_block  # already short

    # Extract ₹ amounts and percentages
    amounts = re.findall(r"₹[\d,]+(?:\.\d+)?", trend_block)
    percents = re.findall(r"[+-]?\d+(?:\.\d+)?%", trend_block)

    if not amounts and not percents:
        # No numbers found, just truncate
        return trend_block[:200] + "…\n" if len(trend_block) > 200 else trend_block

    # Keep the trend block but strip excessive whitespace
    compressed = re.sub(r"\n\s*\n", "\n", trend_block)
    compressed = re.sub(r"  +", " ", compressed)
    return compressed
