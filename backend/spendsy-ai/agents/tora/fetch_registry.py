"""
Plugin registry for universal expense intelligence.

A FetchPlugin is a self-describing module for one spend category. Each plugin
declares its entity keys (the words that trigger it), its fetch profile (which
sub-fetchers to run), a token budget for prompt injection, an async fetcher for
live data, and a sync fallback for guaranteed zero-latency response when the
live path times out or errors.

The universal engine (stage 2) walks this registry; nothing here should know
about any specific category.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable


class FetchStrategy(str, Enum):
    """Honest declaration of what class of data a plugin produces.

    The assembler reads this to render the right confidence footer: we
    never pretend a curated YAML is live, and we never hedge a live API
    result unnecessarily. Users (and the LLM) see an accurate picture.
    """

    LIVE_API = "live_api"                  # gold (IBJA), forex (RBI) — authoritative, <1h freshness
    LIVE_SCRAPE = "live_scrape"            # fuel prices, OTT pages — fragile, daily
    CACHED_DAILY = "cached_daily"          # AMFI NAV, NSE indices — refreshed by warmer
    CACHED_QUARTERLY = "cached_quarterly"  # NHB RESIDEX, PPF rate — regulator cadence
    CURATED_STATIC = "curated_static"      # healthcare, wedding, furniture — YAML, monthly review
    ESTIMATED = "estimated"                # rent index, procedure cost ranges — heuristic
    HYBRID = "hybrid"                      # mixed — some fields live, others curated


# Confidence tier defaults by strategy. Individual facts can override.
STRATEGY_BASE_CONFIDENCE: dict[FetchStrategy, float] = {
    FetchStrategy.LIVE_API: 0.95,
    FetchStrategy.LIVE_SCRAPE: 0.80,
    FetchStrategy.CACHED_DAILY: 0.90,
    FetchStrategy.CACHED_QUARTERLY: 0.75,
    FetchStrategy.CURATED_STATIC: 0.60,
    FetchStrategy.ESTIMATED: 0.45,
    FetchStrategy.HYBRID: 0.70,
}


def confidence_label(score: float) -> str:
    """Map numeric confidence to a user-facing label.

    Kept internal-numeric + external-label — the LLM reasons on the number,
    the footer renders the label. Best of both.
    """
    if score >= 0.85:
        return "high"
    if score >= 0.60:
        return "medium"
    return "low"


@dataclass
class FetchResult:
    """
    What a fetcher (live or fallback) returns.

    - facts: raw data keyed by field name. Each value is a FactValue dict with
      {value, source, fetched_at, ttl_seconds} so the assembler can render
      provenance and the auditor can verify numbers verbatim.
    - options: pre-computed scenario dicts with math already done. The model
      picks which to surface based on user phrasing; it never computes these.
    - constraints: hard rules the model must respect (e.g. "EMI > 40% of
      surplus is not advisable"). Rendered into the prompt as imperatives.
    - provenance: plugin_id, which sub-fetchers hit live vs cache vs fallback,
      and an aggregate `any_fallback_used` flag that drives the subtle footer.
    """

    facts: dict[str, Any] = field(default_factory=dict)
    options: list[dict[str, Any]] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def merge_from(self, other: FetchResult) -> None:
        """Field-level merge: `other` wins per-key where it has a value.

        Used by the engine to layer a successful live fetch on top of the
        pre-computed fallback — so if the live call filled only `spot_price`,
        the merged result keeps fallback's `making_charges` untouched.
        """
        for key, value in other.facts.items():
            if value is not None:
                self.facts[key] = value
        if other.options:
            self.options = other.options  # options are replaced atomically
        if other.constraints:
            # Merge unique constraints without duplicating
            for c in other.constraints:
                if c not in self.constraints:
                    self.constraints.append(c)
        for key, value in other.provenance.items():
            self.provenance[key] = value


# Signatures. Keeping these as bare Callable aliases so plugin authors aren't
# forced to import Protocol just to declare a fetcher.
FetcherFn = Callable[..., Awaitable[FetchResult]]
FallbackFn = Callable[..., FetchResult]


@dataclass
class FetchPlugin:
    """
    Self-describing category plugin.

    Declarative fields (strategy, priority_keys, token_budget, flags) let the
    engine and assembler do their job without any per-category branching.
    """

    plugin_id: str
    entity_keys: list[str]
    fetch_profile: list[str]
    token_budget: int
    fetcher: FetcherFn
    fallback: FallbackFn
    strategy: FetchStrategy = FetchStrategy.CURATED_STATIC
    priority_keys: list[str] = field(default_factory=list)
    sebi_disclaimer: bool = False
    forex_needed: bool = False
    critical_freshness: bool = False
    # Optional: if set, the engine invokes reconcile_fn(facts) after merging
    # live + fallback to resolve source conflicts (e.g. IBJA vs MCX gold).
    reconcile_fn: Callable[[dict], dict] | None = None


@dataclass
class PluginMatch:
    """
    Resolver output. `role` is set by the composition rule in stage 2 —
    primary drives the answer voice, supporting contributes <=30% of budget.
    """

    plugin_id: str
    entity: str
    score: float
    role: str = "primary"  # "primary" | "supporting"


PLUGIN_REGISTRY: dict[str, FetchPlugin] = {}


def register(plugin: FetchPlugin) -> FetchPlugin:
    """Register a plugin under its `plugin_id`.

    Re-registering the same id is allowed and intentional — the package
    __init__ calls `register_all_plugins()` on import, and multiple imports
    should be idempotent. Later registrations overwrite earlier ones.
    """
    PLUGIN_REGISTRY[plugin.plugin_id] = plugin
    return plugin


def get_plugin(plugin_id: str) -> FetchPlugin | None:
    return PLUGIN_REGISTRY.get(plugin_id)


def fact(
    value: Any,
    source: str,
    fetched_at: str | None = None,
    ttl_seconds: int | None = None,
    confidence: float = 0.6,
) -> dict[str, Any]:
    """Convenience builder for a provenance-tagged fact value.

    Not required — fetchers can construct the dict directly — but keeps the
    12 plugin modules from each reinventing the same pattern. Confidence
    defaults to curated-static baseline; live fetchers override upward.
    """
    return {
        "value": value,
        "source": source,
        "fetched_at": fetched_at,
        "ttl_seconds": ttl_seconds,
        "confidence": confidence,
    }
