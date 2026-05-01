"""
Context Packer — Phase 2.

Replaces the rule-based context_compressor with a retrieval-ranked packer.

Pipeline:
  retrieved_chunks (from retrieval_engine)
  + compressed_transactions (from existing context_compressor)
  + market_block (from existing market_context_builder)
  -> ranked merge -> token budget cap by tier -> final context string

Token budgets (approximate chars, 1 token ~ 4 chars):
  FREE:       4000 tokens -> 16000 chars
  PRO:        12000 tokens -> 48000 chars
  ENTERPRISE: 20000 tokens -> 80000 chars

Ranking priority within budget:
  1. Live chunks score >= 0.75 (high-confidence fresh data)
  2. Static KB chunks score >= 0.60 (relevant rules)
  3. Compressed transactions (always included, capped at 800 chars)
  4. Market block (included if budget remains)
  5. Lower-scoring chunks (best-effort)
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Tier -> char budget
TIER_CHAR_BUDGETS: dict[str, int] = {
    "free":       16_000,
    "pro":        48_000,
    "enterprise": 80_000,
}
DEFAULT_BUDGET = 16_000

# Minimum chars reserved for transaction block
TX_BLOCK_RESERVE = 3_200    # ~800 tokens

# Score thresholds
HIGH_CONF_SCORE = 0.75
MED_CONF_SCORE  = 0.60


def _section(title: str, body: str) -> str:
    if not body or not body.strip():
        return ""
    return f"### {title}\n{body.strip()}\n"


def pack_context(
    query: str,
    retrieved_chunks: list[dict],
    compressed_transactions: str = "",
    market_block: str = "",
    tier: str = "free",
    user_profile: Optional[dict[str, Any]] = None,
) -> str:
    """
    Merge and trim all context sources into a single prompt-ready block.

    Args:
        query:                  User query (for logging/debug).
        retrieved_chunks:       Output of retrieval_engine.retrieve().
        compressed_transactions: Output of context_compressor.compress_transactions().
        market_block:           Output of market_context_builder.build_market_context_block().
        tier:                   User tier string ("free" / "pro" / "enterprise").
        user_profile:           Optional user profile for personalisation hints.

    Returns:
        Single string to inject into TORA system prompt.
    """
    budget = TIER_CHAR_BUDGETS.get(tier.lower(), DEFAULT_BUDGET)
    used = 0
    sections: list[str] = []

    # ── 1. Transaction block (always first, guaranteed slot) ─────────────────
    if compressed_transactions:
        tx_chars = min(len(compressed_transactions), TX_BLOCK_RESERVE)
        tx_text = compressed_transactions[:tx_chars]
        block = _section("Recent Transactions", tx_text)
        sections.append(block)
        used += len(block)

    remaining = budget - used

    # ── 2. High-confidence live chunks ──────────────────────────────────────
    high_live = [c for c in retrieved_chunks
                 if c.get("source") == "live_chunk" and c.get("adjusted_score", 0) >= HIGH_CONF_SCORE]
    for chunk in high_live:
        text = chunk.get("text") or ""   # guard missing text key
        if not text:
            continue
        url  = chunk.get("url", "")
        block = _section(
            f"Live Data ({url[:60] or 'web'})",
            text[:min(len(text), remaining // 2)],
        )
        if len(block) > remaining:
            break   # guard is now BEFORE append — no overflow
        sections.append(block)
        used += len(block)
        remaining = budget - used

    # ── 3. Relevant static KB chunks ────────────────────────────────────────
    static_chunks = [c for c in retrieved_chunks
                     if c.get("source") == "static_kb" and c.get("adjusted_score", 0) >= MED_CONF_SCORE]
    for chunk in static_chunks:
        text = chunk.get("text") or ""   # guard missing text key
        if not text:
            continue
        cat  = chunk.get("category", "rules")
        block = _section(f"Financial Rules ({cat})", text[:min(len(text), remaining // 2)])
        if len(block) > remaining:
            break   # guard before append
        sections.append(block)
        used += len(block)
        remaining = budget - used

    # ── 4. Market block ─────────────────────────────────────────────────────
    if market_block and remaining > 500:
        block = _section("Market Context", market_block[:min(len(market_block), remaining)])
        if len(block) <= remaining:
            sections.append(block)
            used += len(block)
            remaining = budget - used

    # ── 5. Remaining chunks (best-effort) ────────────────────────────────────
    used_ids = set()
    for chunk in retrieved_chunks:
        if chunk.get("source") == "live_chunk" and chunk.get("adjusted_score", 0) >= HIGH_CONF_SCORE:
            continue
        if chunk.get("source") == "static_kb" and chunk.get("adjusted_score", 0) >= MED_CONF_SCORE:
            continue
        chunk_id = chunk.get("id") or chunk.get("url", "") + str(chunk.get("chunk_idx", ""))
        if chunk_id in used_ids:
            continue
        used_ids.add(chunk_id)
        text = chunk.get("text") or ""
        if not text:
            continue
        block = _section("Additional Context", text[:min(len(text), remaining // 3)])
        if len(block) > remaining:
            break
        sections.append(block)
        used += len(block)
        remaining = budget - used

    result = "\n".join(s for s in sections if s)

    logger.info(
        "context_packer: tier=%s budget=%d used=%d chunks=%d",
        tier, budget, used, len(retrieved_chunks),
    )
    return result


def pack_context_for_tora(
    query: str,
    transactions: list[dict],
    user_profile: Optional[dict[str, Any]] = None,
    fetch_results: Optional[list] = None,
    tier: str = "free",
) -> str:
    """
    High-level convenience wrapper called from tora_agent.py.

    Runs retrieval + live chunk storage from fetch_results,
    then delegates to pack_context().
    """
    from ..context_compressor import compress_transactions
    from ..market_context_builder import build_market_context_block
    from .retrieval_engine import retrieve
    from .vector_store import store_live_chunks, populate_static_kb

    # Ensure static KB is populated (idempotent)
    populate_static_kb()

    # Store any new live chunks from Phase 1 fetchers
    if fetch_results:
        for fr in fetch_results:
            raw_chunks = getattr(fr, "raw_chunks", None)
            if raw_chunks:
                store_live_chunks(raw_chunks)

    # Retrieve relevant chunks
    city = (user_profile or {}).get("city", "")
    retrieved = retrieve(query, user_profile=user_profile)

    # Compress transactions
    compressed_tx = compress_transactions(transactions, max_items=15, query=query)

    # Build market block
    market_block = ""
    if fetch_results:
        try:
            market_block = build_market_context_block(fetch_results) or ""
        except Exception:
            pass

    return pack_context(
        query=query,
        retrieved_chunks=retrieved,
        compressed_transactions=compressed_tx,
        market_block=market_block,
        tier=tier,
        user_profile=user_profile,
    )
