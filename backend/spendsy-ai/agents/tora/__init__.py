"""
Universal expense intelligence sub-package for TORA.

Stage 1 exposes the registry skeleton, entity resolver, and static fallbacks.
Stage 2+ will add the universal fetch engine and context builder.

Nothing here wires into tora_agent.py yet — importing this package is safe
and side-effect-free apart from populating PLUGIN_REGISTRY.
"""

from .fetch_registry import (
    FetchPlugin,
    FetchResult,
    FetchStrategy,
    PluginMatch,
    PLUGIN_REGISTRY,
    register,
    get_plugin,
    confidence_label,
)
from .entity_resolver import resolve_entities
from .plugins import register_all_plugins

# Populate registry on import. Safe to call multiple times — registration is
# idempotent (same key re-assigns the same plugin).
register_all_plugins()

# Engine + context builder are imported AFTER plugins register themselves —
# the engine reads PLUGIN_REGISTRY at call time, but resolver builds its
# entity-to-plugin map lazily so order matters only for cleanliness.
from .universal_fetch_engine import resolve_and_fetch, summarize_fetch_outcome
from .market_context_builder import build_market_context_block
from .number_auditor import audit_numbers, audit_structured_output
from .thinking_gate import should_enable_thinking
from .expert_router import route_to_expert, inject_expert_preamble
from .context_compressor import (
    compress_transactions,
    compact_extras,
    compress_history,
    compress_trends,
)

__all__ = [
    "FetchPlugin",
    "FetchResult",
    "FetchStrategy",
    "PluginMatch",
    "PLUGIN_REGISTRY",
    "register",
    "get_plugin",
    "resolve_entities",
    "resolve_and_fetch",
    "summarize_fetch_outcome",
    "build_market_context_block",
    "audit_numbers",
    "audit_structured_output",
    "confidence_label",
    "should_enable_thinking",
    "route_to_expert",
    "inject_expert_preamble",
    "compress_transactions",
    "compact_extras",
    "compress_history",
    "compress_trends",
]
