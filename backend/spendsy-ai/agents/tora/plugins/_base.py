"""
Shared helpers for plugin modules.

`build_fallback_from_yaml` constructs a FetchResult from the YAML blob for
a given plugin_id. Every plugin's fallback() simply returns this — no
per-category logic lives here.

`stub_fetcher` is a no-op async fetcher used until the real live fetcher
is built in stage 4+. It returns an empty FetchResult; the engine's
field-level merge means the YAML fallback becomes the effective result
with zero lag.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ..fetch_registry import (
    STRATEGY_BASE_CONFIDENCE,
    FetchResult,
    FetchStrategy,
    PLUGIN_REGISTRY,
)
from ..static_fallbacks import get_fallback


def _plugin_strategy(plugin_id: str) -> FetchStrategy:
    """Lookup this plugin's declared strategy, defaulting to curated-static.

    Called at fallback-build time, after plugins have registered themselves.
    """
    plugin = PLUGIN_REGISTRY.get(plugin_id)
    if plugin is None:
        return FetchStrategy.CURATED_STATIC
    return plugin.strategy


def build_fallback_from_yaml(plugin_id: str) -> FetchResult:
    """Materialise a FetchResult from this plugin's YAML fallback.

    The YAML file's `facts`, `options`, and `constraints` flow through as-is.
    Provenance is synthesised from the YAML's `updated_at` and `source`
    fields so the assembler's subtle footer has what it needs. Confidence
    is derived from the plugin's strategy — curated-static YAML always
    gets the CURATED_STATIC baseline regardless of which plugin it's for.
    """
    blob = get_fallback(plugin_id)
    facts_raw = blob.get("facts", {}) or {}
    options_raw = blob.get("options", []) or []
    constraints_raw = blob.get("constraints", []) or []

    source_label = blob.get("source", f"{plugin_id} static fallback")
    updated_at = blob.get("updated_at", "unknown")

    # Fallback data is always CURATED_STATIC class regardless of whether the
    # plugin's live path is LIVE_API — we're materialising the fallback, not
    # the live result. The engine's field-level merge will upgrade confidence
    # per-field when live data lands on top.
    fallback_confidence = STRATEGY_BASE_CONFIDENCE[FetchStrategy.CURATED_STATIC]

    facts: dict[str, dict] = {}
    for key, value in facts_raw.items():
        facts[key] = {
            "value": value,
            "source": source_label,
            "fetched_at": updated_at,
            "ttl_seconds": None,  # static data has no TTL
            "confidence": fallback_confidence,
        }

    return FetchResult(
        facts=facts,
        options=list(options_raw),
        constraints=list(constraints_raw),
        provenance={
            "plugin_id": plugin_id,
            "strategy": _plugin_strategy(plugin_id).value,
            "any_fallback_used": True,
            "fallback_updated_at": updated_at,
            "fallback_source": source_label,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        },
    )


async def stub_fetcher(*_args, **_kwargs) -> FetchResult:
    """Placeholder async fetcher.

    Returns an empty FetchResult. Stage 1 ships with all 12 plugins using
    this — the engine's parallel fallback path means the YAML content
    becomes the answer, which is exactly what we want before real API
    integrations land in stage 4+.
    """
    return FetchResult()
