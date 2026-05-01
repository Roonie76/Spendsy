"""
RAG layer — Phase 2.

Exports:
  retrieve            — semantic search across static_kb + live_chunks
  pack_context_for_tora — high-level context builder for tora_agent
  store_live_chunks   — store Phase 1 fetcher chunks into live store
  populate_static_kb  — seed static KB (call once at startup)
"""
from .retrieval_engine import retrieve, detect_query_intents
from .context_packer import pack_context, pack_context_for_tora
from .vector_store import (
    store_live_chunks,
    query_live_chunks,
    query_static_kb,
    populate_static_kb,
    embed_text,
)

__all__ = [
    "retrieve",
    "detect_query_intents",
    "pack_context",
    "pack_context_for_tora",
    "store_live_chunks",
    "query_live_chunks",
    "query_static_kb",
    "populate_static_kb",
    "embed_text",
]
