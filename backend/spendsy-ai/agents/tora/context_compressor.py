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

def compress_transactions(transactions: List[Dict[str, Any]], max_items: int = 15, query: str = "") -> str:
    """Compress transaction list into a dense block.

    Instead of individual lines, group by category and show:
    - Top 5 categories with totals
    - Notable transactions: outliers (>1.5x median) OR matches for query keywords.
    """
    if not transactions:
        return ""

    # Aggregate by category
    cat_totals: Dict[str, float] = {}
    cat_counts: Dict[str, int] = {}
    all_amounts: List[float] = []
    
    # Keyword matching for query-relevance
    query_terms = set(re.findall(r"\w+", (query or "").lower()))
    important_keywords = {"card", "bill", "emi", "loan", "rent", "tax", "insurance", "salary", "subscription"}
    
    # We'll use a larger window for analysis but only list a few
    analysis_items = transactions[:max_items * 2] 
    
    for tx in analysis_items:
        try:
            amt = abs(float(tx.get("amount") or 0))
        except (TypeError, ValueError):
            amt = 0.0
        if amt > 0:
            all_amounts.append(amt)

    # Threshold for outliers (lowered to 1.5x for more visibility)
    threshold = 0
    if all_amounts:
        sorted_amts = sorted(all_amounts)
        median = sorted_amts[len(sorted_amts) // 2]
        threshold = median * 1.5 if median > 0 else 0

    notable_txs = []
    seen_ids = set()

    # Pass 1: Find transactions relevant to the query or important keywords
    for tx in analysis_items:
        title = str(tx.get("title", "")).lower()
        try:
            amt = abs(float(tx.get("amount") or 0))
        except (TypeError, ValueError):
            amt = 0.0
        
        # Is it relevant to what the user asked?
        is_query_relevant = any(term in title for term in query_terms if len(term) > 3)
        # Is it a generally "important" transaction type?
        is_important = any(kw in title for kw in important_keywords)
        
        if (is_query_relevant or is_important) and tx.get("id") not in seen_ids:
            notable_txs.append(tx)
            seen_ids.add(tx.get("id"))
            if len(notable_txs) >= 5: break

    # Pass 2: Add large outliers if we have space
    if len(notable_txs) < 8:
        for tx in analysis_items:
            try:
                amt = abs(float(tx.get("amount") or 0))
            except (TypeError, ValueError):
                amt = 0.0
            if amt > threshold and tx.get("id") not in seen_ids:
                notable_txs.append(tx)
                seen_ids.add(tx.get("id"))
                if len(notable_txs) >= 8: break

    # Build category summary for the recent window
    for tx in transactions[:max_items]:
        cat = tx.get("category") or "other"
        try:
            amt = float(tx.get("amount") or 0)
        except (TypeError, ValueError):
            amt = 0.0
        cat_totals[cat] = cat_totals.get(cat, 0) + amt
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    lines = []
    top_cats = sorted(cat_totals.items(), key=lambda x: abs(x[1]), reverse=True)[:6]
    for cat, total in top_cats:
        count = cat_counts[cat]
        lines.append(f"{cat}: ₹{total:,.0f} ({count} txns)")

    result = "=== RECENT ACTIVITY (compressed) ===\n"
    result += " | ".join(lines) + "\n"

    if notable_txs:
        # Sort notable by relevance (query matches first) then amount
        def _safe_amt(tx: dict) -> float:
            try:
                return abs(float(tx.get("amount") or 0))
            except (TypeError, ValueError):
                return 0.0

        notable_txs.sort(key=lambda x: (
            any(term in str(x.get("title", "")).lower() for term in query_terms if len(term) > 3),
            _safe_amt(x)
        ), reverse=True)

        result += "Notable: "
        result += ", ".join(
            f"{tx.get('title', '?')} {'+' if tx.get('type')=='income' else '-'}₹{_safe_amt(tx):,.0f}"
            for tx in notable_txs[:6] # Show up to 6 notable items
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
