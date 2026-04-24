"""
Static fallback loader.

Each category has one YAML file in this directory, curated by hand and
updated monthly. At module import time we load every YAML into
`FALLBACK_DATA`, so fallback lookup is a dict access (sub-ms) and the
engine can merge it in parallel with the live fetch.

YAML shape (loose — plugins consume their own category's blob):
    updated_at: "2026-04-24"
    source: "IBJA daily rate + manual curation"
    notes: "Review monthly when GST slabs change."
    facts:
      spot_price_per_10g_inr_22k: 72400
      making_charges_pct_range: [8, 18]
      gst_pct: 3
    options: []
    constraints:
      - "Making charges are not recoverable on resale — prefer coins/bars for investment."
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover — dev safety net
    yaml = None  # Plugins must handle missing YAML gracefully

logger = logging.getLogger(__name__)

_FALLBACK_DIR = Path(__file__).parent
FALLBACK_DATA: dict[str, dict[str, Any]] = {}


def _load_all() -> None:
    """Populate FALLBACK_DATA from every *.yaml file in this directory."""
    if yaml is None:
        logger.warning(
            "PyYAML not installed — TORA fallbacks unavailable. "
            "Install pyyaml to enable zero-latency category responses."
        )
        return
    for yaml_path in _FALLBACK_DIR.glob("*.yaml"):
        plugin_id = yaml_path.stem  # e.g. "gold.yaml" → "gold"
        try:
            with yaml_path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            if not isinstance(data, dict):
                logger.warning(
                    "Fallback %s did not parse to a dict, skipping", yaml_path.name
                )
                continue
            FALLBACK_DATA[plugin_id] = data
        except Exception as e:
            logger.exception("Failed to load fallback %s: %s", yaml_path.name, e)


_load_all()


def get_fallback(plugin_id: str) -> dict[str, Any]:
    """Return the raw fallback blob for a plugin, or an empty dict.

    Returning {} (not None) lets callers always do `data.get("facts", {})`
    without a None check.
    """
    return FALLBACK_DATA.get(plugin_id, {})
