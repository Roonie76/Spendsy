"""
Retrieval Engine — Phase 2.

Takes query + user financial profile -> searches both static_kb and live_chunks
-> applies metadata filters -> returns top-K ranked chunks ready for context packer.

Filter logic:
  - intent=tax        -> category filter "tax" on static_kb
  - intent=banking    -> category filter "banking"
  - intent=investment -> category filter "investment"
  - intent=mobility   -> live_chunks only (car prices, bank rates)
  - default           -> search all

Scoring: cosine similarity from vector_store, with a +0.05 boost for:
  - live chunks fresher than 6h (recency boost)
  - static_kb chunks whose category matches detected intent
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from .vector_store import query_static_kb, query_live_chunks

logger = logging.getLogger(__name__)

# Intent -> static_kb category mapping
INTENT_CATEGORY_MAP: dict[str, str] = {
    "tax":        "tax",
    "banking":    "banking",
    "loan":       "banking",
    "emi":        "banking",
    "investment": "investment",
    "sip":        "investment",
    "nps":        "investment",
    "ppf":        "investment",
    "elss":       "investment",
    "credit":     "banking",
    "gst":        "tax",
    "itr":        "tax",
    "home_loan":  "tax",
}

# Keywords to detect intents from query text
INTENT_PATTERNS: dict[str, list[str]] = {
    "tax":        [r"\btax\b", r"\bitr\b", r"\bslab\b", r"\bdeduction\b",
                   r"\bregime\b", r"\b80c\b", r"\bcess\b", r"\bsurcharge\b"],
    "banking":    [r"\bloan\b", r"\bemi\b", r"\binterest\s+rate\b",
                   r"\bcredit\s+card\b", r"\bfd\b", r"\bfixed\s+deposit\b",
                   r"\bmclr\b", r"\brepo\b"],
    "investment": [r"\bsip\b", r"\bmutual\s+fund\b", r"\bnps\b", r"\bppf\b",
                   r"\belss\b", r"\bltcg\b", r"\bstcg\b", r"\bstock\b",
                   r"\bequity\b"],
    "mobility":   [r"\bcar\b", r"\bbike\b", r"\bev\b", r"\bscooter\b",
                   r"\bvehicle\b", r"\bauto\s+loan\b", r"\bon.?road\b"],
}


def detect_query_intents(query: str) -> list[str]:
    """Return list of matched intents for a query (ordered by match count)."""
    q = query.lower()
    scores: dict[str, int] = {}
    for intent, patterns in INTENT_PATTERNS.items():
        count = sum(1 for p in patterns if re.search(p, q))
        if count > 0:
            scores[intent] = count
    return sorted(scores, key=lambda k: -scores[k])


def _recency_boost(chunk: dict) -> float:
    """+0.05 if fetched within last 6 hours."""
    fetched_at = chunk.get("fetched_at", "")
    if not fetched_at:
        return 0.0
    try:
        from datetime import datetime, timezone
        ft = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        age_h = (datetime.now(timezone.utc) - ft).total_seconds() / 3600
        return 0.05 if age_h < 6 else 0.0
    except Exception:
        return 0.0


def retrieve(
    query: str,
    user_profile: Optional[dict[str, Any]] = None,
    n_static: int = 3,
    n_live: int = 3,
) -> list[dict]:
    """
    Main retrieval function.

    Args:
        query:        User's natural-language query.
        user_profile: Dict with keys like {city, surplus, tier, income}.
                      Used to bias retrieval (e.g. city -> prefer local car prices).
        n_static:     Max chunks from static_kb.
        n_live:       Max chunks from live store.

    Returns:
        List of chunk dicts sorted by adjusted score DESC.
        Each chunk: {text, source, score, category?, url?, fetched_at?}
    """
    intents = detect_query_intents(query)
    primary_intent = intents[0] if intents else None

    # Determine static_kb category filter
    static_category = None
    if primary_intent and primary_intent != "mobility":
        static_category = INTENT_CATEGORY_MAP.get(primary_intent)

    # Query both stores
    static_results = [] if primary_intent == "mobility" else \
        query_static_kb(query, n_results=n_static, category=static_category)

    live_results = query_live_chunks(query, n_results=n_live)

    # Apply boosts
    all_results = []
    for chunk in static_results:
        adj_score = chunk["score"]
        if static_category and chunk.get("category") == static_category:
            adj_score = min(1.0, adj_score + 0.05)
        chunk["adjusted_score"] = round(adj_score, 4)
        all_results.append(chunk)

    for chunk in live_results:
        adj_score = chunk["score"] + _recency_boost(chunk)
        chunk["adjusted_score"] = round(min(1.0, adj_score), 4)
        all_results.append(chunk)

    all_results.sort(key=lambda x: -x["adjusted_score"])

    logger.info(
        "retrieve: query=%r intents=%s -> %d static + %d live chunks",
        query[:60], intents, len(static_results), len(live_results),
    )
    return all_results
