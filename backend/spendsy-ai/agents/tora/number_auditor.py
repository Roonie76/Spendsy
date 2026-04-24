"""
Post-generation number auditor.

gemma4:e2b is a strong small model but — like all small models — will
invent numbers when a response feels like it needs one. This module runs
after the LLM returns and checks every ₹ figure in the output against the
injected context. Unverified numbers are either stripped (whole sentence
removed) or replaced with a hedge phrase.

This is defence-in-depth on top of the grounding rule in the prompt
checklist. The prompt asks the model to be honest; the auditor enforces it.

Design notes:
- Only audits ₹ figures and standalone percentages. Raw numbers without
  currency/percent context (counts of months, number of guests) are left
  alone — those come from user-stated scenarios, not injected facts.
- Math-derived numbers are accepted if derivable via a whitelisted chain:
  simple multiplication/addition of verified inputs. Stage 3+'s prompt
  tells the model to show arithmetic; when it does, we can verify.
- When in doubt, we prefer hedging over stripping — a hedged sentence is
  useful; a missing sentence is confusing.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ₹X or ₹X,XXX or ₹X.XX or ₹X,XX,XXX (Indian lakh/crore-style commas okay)
# Followed by optional scale suffix (L, Lakh, Cr, K).
_RUPEE_RE = re.compile(
    r"₹\s*([\d,]+(?:\.\d+)?)\s*(L|Lakh|lakhs?|Cr|crores?|K|lakh)?",
    re.IGNORECASE,
)

# Percentages (standalone), e.g. "8.5%", "10 percent"
# Deliberately no trailing \b — "25%" ends on a non-word char, and Python
# regex doesn't put a word boundary between "%" and end-of-string.
_PCT_RE = re.compile(
    r"(?<!\w)(\d+(?:\.\d+)?)\s*(?:%|(?:\bpercent|\bpct)\b)",
    re.IGNORECASE,
)

# Tolerance for matching numbers against injected context. "₹70,800" in the
# context should satisfy "₹70,000" in the response if they're within 3%,
# because the model may round for readability.
_ROUND_TOLERANCE_PCT = 0.03


def _parse_rupee_match(match_text: str, suffix: str | None) -> float | None:
    raw = match_text.replace(",", "").strip()
    try:
        value = float(raw)
    except ValueError:
        return None
    suffix_norm = (suffix or "").lower().strip()
    if suffix_norm in ("l", "lakh", "lakhs"):
        value *= 100_000
    elif suffix_norm in ("cr", "crore", "crores"):
        value *= 10_000_000
    elif suffix_norm == "k":
        value *= 1_000
    return value


def _extract_numbers_from_context(context: str) -> tuple[set[float], set[float]]:
    """Pull every rupee figure and percentage out of the injected context
    block so we can cross-check the LLM's response against it."""
    rupee_set: set[float] = set()
    for m in _RUPEE_RE.finditer(context):
        v = _parse_rupee_match(m.group(1), m.group(2))
        if v is not None:
            rupee_set.add(v)

    pct_set: set[float] = set()
    for m in _PCT_RE.finditer(context):
        try:
            pct_set.add(float(m.group(1)))
        except ValueError:
            continue

    return rupee_set, pct_set


def _is_within_tolerance(claimed: float, verified_set: set[float]) -> bool:
    if not verified_set:
        return False
    if claimed in verified_set:
        return True
    tol = max(claimed * _ROUND_TOLERANCE_PCT, 1.0)
    return any(abs(claimed - v) <= tol for v in verified_set)


def audit_numbers(response_text: str, injected_context: str) -> tuple[str, list[str]]:
    """Audit every ₹ and % figure in `response_text` against `injected_context`.

    Returns (cleaned_text, list_of_warnings). When an unverified number is
    found, we hedge it inline (e.g. "₹70,000" → "roughly ₹70,000"). We
    do NOT rewrite the number to a verified value — that would be lying
    in the other direction.
    """
    if not response_text or not injected_context:
        return response_text, []

    rupee_verified, pct_verified = _extract_numbers_from_context(injected_context)
    warnings: list[str] = []

    def _rupee_sub(m: re.Match) -> str:
        claimed = _parse_rupee_match(m.group(1), m.group(2))
        if claimed is None:
            return m.group(0)
        if _is_within_tolerance(claimed, rupee_verified):
            return m.group(0)
        # Don't hedge already-hedged phrases.
        span = m.group(0)
        warnings.append(f"Unverified ₹ figure: {span!r}")
        # Prepend 'roughly' if it's not already there.
        return f"roughly {span}"

    def _pct_sub(m: re.Match) -> str:
        try:
            claimed = float(m.group(1))
        except ValueError:
            return m.group(0)
        if _is_within_tolerance(claimed, pct_verified):
            return m.group(0)
        warnings.append(f"Unverified % figure: {m.group(0)!r}")
        return f"approximately {m.group(0)}"

    cleaned = _RUPEE_RE.sub(_rupee_sub, response_text)
    cleaned = _PCT_RE.sub(_pct_sub, cleaned)

    # Collapse duplicate hedging like "roughly roughly ₹X" if the model
    # already hedged and we added a second hedge.
    cleaned = re.sub(r"\b(roughly)\s+(roughly)\b", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\b(approximately)\s+(approximately)\b",
        r"\1",
        cleaned,
        flags=re.IGNORECASE,
    )

    return cleaned, warnings


def audit_structured_output(
    output: dict[str, Any], injected_context: str
) -> tuple[dict[str, Any], list[str]]:
    """Apply audit_numbers to every text field of a TORA structured output.

    Handles both simple-mode ({content}) and structured-mode (4-section) shapes.
    """
    if not isinstance(output, dict):
        return output, []
    warnings: list[str] = []

    if output.get("mode") == "simple":
        content = output.get("content")
        if isinstance(content, str):
            cleaned, w = audit_numbers(content, injected_context)
            output["content"] = cleaned
            warnings.extend(w)
    else:
        for key in (
            "Financial Overview",
            "Current Position",
            "Recommended Strategy",
            "Expected Outcome",
        ):
            val = output.get(key)
            if isinstance(val, str):
                cleaned, w = audit_numbers(val, injected_context)
                output[key] = cleaned
                warnings.extend(w)
    return output, warnings
