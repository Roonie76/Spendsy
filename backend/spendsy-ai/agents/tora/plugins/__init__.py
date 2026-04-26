"""
Plugin registration.

Each plugin module defines a `PLUGIN: FetchPlugin` module-level object.
`register_all_plugins()` walks this package and calls `register()` on each.

Stage 1: plugins ship with a working fallback + a stub async fetcher that
immediately returns FetchResult() — the engine's merge logic means the
empty result gets overlaid by the fallback, so TORA already has useful
data for every category.

Stage 4+ replaces the stubs with real async fetchers one plugin at a time.
"""

from __future__ import annotations

import logging

from ..fetch_registry import register
from . import (
    appliances,
    education,
    electronics,
    furniture,
    gold,
    healthcare,
    investments,
    lifestyle,
    mobility,
    real_estate,
    travel,
    wedding,
    browser_fetch,
)

logger = logging.getLogger(__name__)

_ALL_PLUGIN_MODULES = [
    mobility,
    real_estate,
    electronics,
    appliances,
    travel,
    gold,
    investments,
    education,
    healthcare,
    wedding,
    furniture,
    lifestyle,
    browser_fetch,
]


def register_all_plugins() -> None:
    """Register every plugin module's PLUGIN object. Idempotent."""
    for mod in _ALL_PLUGIN_MODULES:
        plugin = getattr(mod, "PLUGIN", None)
        if plugin is None:
            logger.warning(
                "Plugin module %s has no PLUGIN attribute — skipping",
                mod.__name__,
            )
            continue
        register(plugin)
