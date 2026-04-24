"""
Universal Intelligence Engine.

Takes a user message, resolves it to plugin matches, and fires each matched
plugin's fetcher + fallback **in parallel**. Applies a hard total budget
(800ms default) across the whole fan-out. Returns ready-to-render
FetchResults merged field-by-field — live wins, fallback fills gaps.

The key invariant: the user never waits for a slow fetcher. Fallbacks are
sync and pre-resolved; live fetchers have 600ms each but the whole batch
is bounded by 800ms total. A 3s external API simply never enters the
response.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from .entity_resolver import resolve_entities
from .fetch_registry import (
    PLUGIN_REGISTRY,
    FetchPlugin,
    FetchResult,
    FetchStrategy,
    PluginMatch,
)

logger = logging.getLogger(__name__)

TOTAL_BUDGET_SECONDS = 0.8  # hard cap across ALL fetchers for one query
PER_FETCHER_BUDGET_SECONDS = 0.6  # per-plugin live-fetch budget


async def _fire_one_plugin(
    match: PluginMatch,
    plugin: FetchPlugin,
    user_surplus: float | None,
    user_city: str | None,
) -> tuple[PluginMatch, FetchResult]:
    """Fire one plugin: pre-compute fallback sync, launch live fetch, merge
    live over fallback when (or if) live returns within budget.
    """
    # Fallback FIRST, synchronously. This guarantees we have a complete
    # answer sitting in memory before any network call happens. If the
    # live fetch never returns, we still ship a full response.
    try:
        fallback_result = plugin.fallback(
            entity=match.entity, surplus=user_surplus, city=user_city
        )
    except Exception as e:
        logger.warning("Fallback for %s raised: %s", plugin.plugin_id, e)
        fallback_result = FetchResult()

    # Ensure fallback result carries the plugin's declared strategy in
    # provenance — the assembler reads this for the footer.
    fallback_result.provenance.setdefault("plugin_id", plugin.plugin_id)
    fallback_result.provenance.setdefault("strategy", plugin.strategy.value)
    fallback_result.provenance.setdefault("role", match.role)

    # Launch live fetch with a per-plugin timeout. Non-LIVE_API plugins with
    # stub fetchers just return empty quickly; we still await them for
    # consistency.
    try:
        live_result = await asyncio.wait_for(
            plugin.fetcher(
                entity=match.entity, surplus=user_surplus, city=user_city
            ),
            timeout=PER_FETCHER_BUDGET_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.debug("Live fetch timeout for %s", plugin.plugin_id)
        live_result = FetchResult()
    except Exception as e:
        logger.debug("Live fetch exception for %s: %s", plugin.plugin_id, e)
        live_result = FetchResult()

    # Field-level merge: live wins per-key where present; fallback fills gaps.
    merged = fallback_result
    if live_result.facts or live_result.options or live_result.constraints:
        merged.merge_from(live_result)
        merged.provenance["any_live_used"] = True
    else:
        merged.provenance["any_live_used"] = False

    # Apply optional reconciliation hook (stage 4+ gold/investments may set
    # this to resolve conflicts between two live sources).
    if plugin.reconcile_fn is not None:
        try:
            merged.facts = plugin.reconcile_fn(merged.facts)
        except Exception as e:
            logger.warning("Reconcile fn failed for %s: %s", plugin.plugin_id, e)

    return match, merged


async def resolve_and_fetch(
    message: str,
    user_surplus: float | None = None,
    user_city: str | None = None,
) -> list[tuple[PluginMatch, FetchResult]]:
    """Main entry point.

    Returns a list of (match, result) tuples in priority order (primary first).
    Empty list = no plugin matched; caller should skip enrichment entirely
    and use TORA's profile-only path.

    The caller handles whatever comes back — even if every fetcher failed,
    the fallbacks mean each tuple has a full FetchResult.
    """
    matches = resolve_entities(message)
    if not matches:
        return []

    plugins_and_matches: list[tuple[PluginMatch, FetchPlugin]] = []
    for match in matches:
        plugin = PLUGIN_REGISTRY.get(match.plugin_id)
        if plugin is None:
            logger.warning(
                "Resolver returned unregistered plugin_id=%s", match.plugin_id
            )
            continue
        plugins_and_matches.append((match, plugin))

    if not plugins_and_matches:
        return []

    # Fan out all plugin fetches concurrently, guarded by one total-budget
    # wait_for. Gather with return_exceptions so a single plugin raising
    # doesn't poison the batch.
    tasks = [
        _fire_one_plugin(match, plugin, user_surplus, user_city)
        for match, plugin in plugins_and_matches
    ]

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=TOTAL_BUDGET_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.info(
            "Universal engine total budget exceeded (%.2fs) — returning fallbacks",
            TOTAL_BUDGET_SECONDS,
        )
        # Partial results: rebuild fallbacks-only for each match so the
        # caller still gets a complete list. Sync fallback is fast enough
        # that this path adds negligible latency.
        return [
            (match, _safe_fallback(plugin, match, user_surplus, user_city))
            for match, plugin in plugins_and_matches
        ]

    # Filter out gather-level exceptions; substitute sync fallback for those.
    final: list[tuple[PluginMatch, FetchResult]] = []
    for (match, plugin), outcome in zip(plugins_and_matches, results):
        if isinstance(outcome, BaseException):
            logger.warning(
                "Task for %s raised %s — using fallback",
                plugin.plugin_id,
                type(outcome).__name__,
            )
            final.append(
                (match, _safe_fallback(plugin, match, user_surplus, user_city))
            )
        else:
            final.append(outcome)  # (match, merged_result)

    return final


def _safe_fallback(
    plugin: FetchPlugin,
    match: PluginMatch,
    user_surplus: float | None,
    user_city: str | None,
) -> FetchResult:
    """Sync fallback with exception guard — used when the live path timed
    out at the total-budget level."""
    try:
        result = plugin.fallback(
            entity=match.entity, surplus=user_surplus, city=user_city
        )
    except Exception as e:
        logger.warning(
            "Sync fallback for %s raised: %s — returning empty",
            plugin.plugin_id,
            e,
        )
        result = FetchResult()
    result.provenance.setdefault("plugin_id", plugin.plugin_id)
    result.provenance.setdefault("strategy", plugin.strategy.value)
    result.provenance.setdefault("role", match.role)
    result.provenance["any_live_used"] = False
    result.provenance["reason"] = "total_budget_exceeded"
    return result


def summarize_fetch_outcome(
    results: list[tuple[PluginMatch, FetchResult]],
) -> dict[str, Any]:
    """Debug/telemetry helper — compact summary of what the engine produced.

    Not called in the hot path; used in tests and integration smoke checks.
    """
    return {
        "plugin_count": len(results),
        "plugins": [
            {
                "plugin_id": match.plugin_id,
                "entity": match.entity,
                "role": match.role,
                "score": match.score,
                "strategy": result.provenance.get("strategy"),
                "any_live_used": result.provenance.get("any_live_used"),
                "fact_count": len(result.facts),
                "constraint_count": len(result.constraints),
            }
            for match, result in results
        ],
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
