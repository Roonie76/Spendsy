"""
Thinking-mode gating.

Gemma 4's thinking mode trades latency (roughly 3x slower) for reasoning
quality. We don't want it on every query — "how much did I spend on food?"
doesn't need it and the slower response feels broken.

Rule: enable thinking mode when ANY of the following is true:
  1. The universal intelligence engine matched at least one track 2 plugin
     (message has a domain entity like car/house/gold/etc.).
  2. The message is >15 words AND contains comparison or hypothetical
     language ("should I", "compare", "which is better", "what if").
  3. The message contains explicit planning verbs ("plan", "strategize",
     "simulate") — these require multi-step thinking.

Otherwise thinking mode is OFF (default).
"""

from __future__ import annotations

import re

_COMPARISON_RE = re.compile(
    r"\b(?:should\s+i|should\s+we|compare|which\s+is\s+better|which\s+one|"
    r"vs\.?|versus|trade[-\s]?off|pros\s+and\s+cons|better\s+to|worth\s+it)\b",
    re.IGNORECASE,
)
_HYPOTHETICAL_RE = re.compile(
    r"\b(?:what\s+if|suppose|assume|imagine|in\s+case|hypothetical|"
    r"what\s+would|if\s+i\s+were)\b",
    re.IGNORECASE,
)
_PLANNING_RE = re.compile(
    r"\b(?:plan(?:ning)?|strategi[sz]e|simulate|forecast|project|roadmap|"
    r"long[-\s]?term|retire(?:ment)?|optimi[sz]e)\b",
    re.IGNORECASE,
)

COMPLEX_WORD_THRESHOLD = 15


def should_enable_thinking(message: str, has_plugin_match: bool) -> bool:
    """Return True when the query warrants thinking mode.

    Called once per query by the agent orchestrator. No side effects.
    """
    if not message:
        return False
    if has_plugin_match:
        return True

    word_count = len(message.split())
    if word_count > COMPLEX_WORD_THRESHOLD:
        if _COMPARISON_RE.search(message) or _HYPOTHETICAL_RE.search(message):
            return True

    if _PLANNING_RE.search(message):
        return True

    return False
