"""
Faithfulness Checker — Production safety layer.

Verifies that numbers the LLM stated in its response are faithful to
the structured output from the strategy ranker. Catches the specific
failure mode where the LLM "drifts" from the injected strategy block
and invents or rounds numbers in ways that change financial meaning.

Difference from calc_verifier:
  calc_verifier  — checks the MATH (EMI formula, SIP formula, etc.)
  faithfulness   — checks the LLM OUTPUT against RANKER OUTPUT
                   (did the model accurately report what the ranker said?)

Examples caught:
  - Ranker says best strategy EMI = ₹14,500 → LLM says ₹12,000
  - Ranker says total cost = ₹8.4L → LLM says ₹6 lakh
  - Ranker says interest saved = ₹1.2L → LLM says ₹80,000
  - Ranker says timeline = 36 months → LLM says "2 years" (fine)
    vs "4 years" (flag)

Tolerance: 5% for soft warning, 20% for hard flag.
Hard flags append a verifier note to the response.
Never suppresses the response entirely — only hedges and logs.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_SOFT_TOL = 0.05   # 5% — soft warning only
_HARD_TOL = 0.20   # 20% — hard flag, append note to response

_RUPEE_RE = re.compile(
    r"(?:Rs\.?|INR|₹)\s*([\d,]+(?:\.\d+)?)\s*(crore|cr|lakh|lakhs?|l|k)?",
    re.IGNORECASE,
)
_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_MONTH_RE = re.compile(r"(\d+)\s*month", re.IGNORECASE)
_YEAR_RE  = re.compile(r"(\d+(?:\.\d+)?)\s*year", re.IGNORECASE)


def _parse_inr(digits: str, suffix: str | None) -> float:
    val = float(digits.replace(",", ""))
    s = (suffix or "").lower().strip()
    if s in ("crore", "cr"):   return val * 1e7
    if s in ("lakh", "lakhs", "l"): return val * 1e5
    if s == "k":                return val * 1e3
    return val


def _extract_rupee(text: str) -> list[float]:
    return [_parse_inr(m.group(1), m.group(2)) for m in _RUPEE_RE.finditer(text)]


def _extract_pct(text: str) -> list[float]:
    return [float(m.group(1)) for m in _PCT_RE.finditer(text)]


def _extract_months(text: str) -> list[int]:
    months: list[int] = []
    for m in _MONTH_RE.finditer(text):
        months.append(int(m.group(1)))
    for m in _YEAR_RE.finditer(text):
        months.append(round(float(m.group(1)) * 12))
    return months


def _rel_err(claimed: float, ref: float) -> float:
    if ref == 0:
        return 0.0 if claimed == 0 else 1.0
    return abs(claimed - ref) / abs(ref)


def _nearest(claimed: float, candidates: list[float]) -> tuple[float, float]:
    if not candidates:
        return 0.0, 1.0
    best = min(candidates, key=lambda c: _rel_err(claimed, c))
    return best, _rel_err(claimed, best)


def _collect_ranker_values(ranked_output: dict[str, Any]) -> dict[str, list[float]]:
    """Pull key numeric fields from ranked_output into typed lists."""
    rupees: list[float] = []
    pcts:   list[float] = []
    months: list[int]   = []

    for s in ranked_output.get("ranked", [ranked_output.get("best", {})]):
        if not isinstance(s, dict):
            continue
        for key in ("monthly_outflow", "monthly_outflow_inr", "total_cost",
                    "total_cost_inr", "interest_paid", "tax_saving"):
            v = s.get(key)
            if v and float(v) > 0:
                rupees.append(float(v))
        rate = s.get("interest_rate") or s.get("rate_pct")
        if rate:
            pcts.append(float(rate))
        tl = s.get("timeline_months")
        if tl:
            months.append(int(tl))

    return {"rupees": rupees, "pcts": pcts, "months": [float(m) for m in months]}


def check_faithfulness(
    response_text: str,
    ranked_output: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """
    Compare ₹/% figures in response_text against ranked_output values.

    Returns:
        (soft_warnings, hard_flags)
        soft_warnings — 5-20% mismatch
        hard_flags    — >20% mismatch or off-by-scale
    """
    if not response_text or not ranked_output:
        return [], []

    ref = _collect_ranker_values(ranked_output)
    soft: list[str] = []
    hard: list[str] = []

    # Check rupee figures
    for claimed in _extract_rupee(response_text):
        if claimed < 500:    # skip trivial amounts
            continue
        best, err = _nearest(claimed, ref["rupees"])
        if not ref["rupees"]:
            break
        # Off-by-10x check (lakh vs crore confusion)
        if err > _HARD_TOL:
            for scale in (10, 0.1, 100, 0.01):
                if _rel_err(claimed * scale, best) < _SOFT_TOL:
                    hard.append(
                        f"Scale error: LLM said ₹{claimed:,.0f} but ranker "
                        f"has ₹{best:,.0f} (off by {scale}x — lakh/crore mix-up?)"
                    )
                    break
            else:
                hard.append(
                    f"Faithfulness: LLM said ₹{claimed:,.0f}, ranker says "
                    f"₹{best:,.0f} ({err*100:.0f}% deviation)"
                )
        elif err > _SOFT_TOL:
            soft.append(
                f"Minor drift: ₹{claimed:,.0f} vs ranker ₹{best:,.0f} "
                f"({err*100:.1f}% — acceptable rounding?)"
            )

    # Check interest rates
    for claimed_r in _extract_pct(response_text):
        if claimed_r < 1 or claimed_r > 45:
            continue   # not an interest rate
        best_r, err_r = _nearest(claimed_r, ref["pcts"])
        if ref["pcts"] and err_r > _HARD_TOL:
            hard.append(
                f"Rate faithfulness: LLM said {claimed_r}%, ranker has "
                f"{best_r}% ({err_r*100:.0f}% deviation)"
            )

    # Check timelines (months)
    for claimed_m in _extract_months(response_text):
        best_m, err_m = _nearest(float(claimed_m), ref["months"])
        if ref["months"] and err_m > _HARD_TOL:
            hard.append(
                f"Timeline faithfulness: LLM said {claimed_m} months, "
                f"ranker has {int(best_m)} months"
            )

    if soft:
        logger.info("faithfulness: %d soft warnings", len(soft))
    if hard:
        logger.warning("faithfulness: %d HARD FLAGS: %s", len(hard), hard)

    return soft, hard


_FAITHFULNESS_NOTE = (
    "\n\n⚠ *One or more figures in this response could not be verified against "
    "the financial model. Please treat all amounts as indicative and confirm "
    "with your bank or a qualified advisor before acting.*"
)


def apply_faithfulness(
    response: dict[str, Any],
    ranked_output: dict[str, Any],
) -> tuple[dict[str, Any], list[str], list[str]]:
    """
    Run faithfulness check and append note to response if hard flags found.

    Returns (patched_response, soft_warnings, hard_flags).
    """
    resp_text = ""
    if response.get("mode") == "simple":
        resp_text = response.get("content", "")
    else:
        resp_text = " ".join(
            str(response.get(k, ""))
            for k in ("Financial Overview", "Current Position",
                      "Recommended Strategy", "Expected Outcome")
        )

    soft, hard = check_faithfulness(resp_text, ranked_output)

    if hard:
        # Append verifier note to the last visible text field
        if response.get("mode") == "simple":
            response["content"] = str(response.get("content", "")) + _FAITHFULNESS_NOTE
        else:
            for key in reversed(("Expected Outcome", "Recommended Strategy",
                                  "Current Position", "Financial Overview")):
                val = response.get(key)
                if isinstance(val, str) and val.strip():
                    response[key] = val + _FAITHFULNESS_NOTE
                    break

    return response, soft, hard
