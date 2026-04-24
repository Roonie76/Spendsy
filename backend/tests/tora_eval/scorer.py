"""Rule-based scorer for TORA golden-question evals.

Given a `GoldenQuestion` and a raw TORA response dict, produces a
`ScoreResult` with per-check pass/fail and a 0–1 overall score.

The scorer is deterministic and hermetic — no LLM calls, no network.
Its checks cover the hard failure modes: wrong numbers, wrong mode,
wrong tool, fabricated figures, persona violations.

For soft qualities (tone, clarity, helpfulness), pair this with the
LLM judge in `judge.py`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .golden_questions import GoldenQuestion


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ScoreResult:
    question_id: str
    checks: List[CheckResult] = field(default_factory=list)

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def total_count(self) -> int:
        return len(self.checks)

    @property
    def score(self) -> float:
        if not self.checks:
            return 1.0
        return self.passed_count / self.total_count

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def failures(self) -> List[CheckResult]:
        return [c for c in self.checks if not c.passed]


# ---------------------------------------------------------------------------
# Response normalization
# ---------------------------------------------------------------------------


def _extract_text(response: Dict[str, Any]) -> str:
    """Pull all user-visible text out of a TORA response, regardless of mode."""
    if not isinstance(response, dict):
        return str(response)

    parts: List[str] = []
    if response.get("mode") == "simple":
        parts.append(str(response.get("content", "")))
    for key in ("Financial Overview", "Current Position", "Recommended Strategy", "Expected Outcome"):
        if response.get(key):
            parts.append(str(response[key]))
    # Legacy fallbacks
    if "content" in response and response.get("mode") != "simple":
        parts.append(str(response["content"]))
    return "\n".join(p for p in parts if p)


def _detect_mode(response: Dict[str, Any]) -> str:
    if response.get("mode") == "simple":
        return "simple"
    if any(response.get(k) for k in ("Financial Overview", "Current Position", "Recommended Strategy", "Expected Outcome")):
        return "structured"
    return "simple"  # Default assumption


def _tool_names(response: Dict[str, Any]) -> List[str]:
    tools = response.get("tool_calls") or []
    if not isinstance(tools, list):
        return []
    return [str(t.get("name", "")) for t in tools if isinstance(t, dict)]


# ---------------------------------------------------------------------------
# Number matching — handles "₹42,310", "42310", "42,310.00", "₹42.3k"
# ---------------------------------------------------------------------------

_NUMBER_TOKEN_RE = re.compile(r"₹?\s?([\d,]+(?:\.\d+)?)(?:\s?(k|K|lakh|cr|crore))?")


def _text_contains_number(text: str, target: float, tolerance: float = 0.01) -> bool:
    """True if `target` appears in `text` in any common Indian-format spelling."""
    if not text:
        return False
    for match in _NUMBER_TOKEN_RE.finditer(text):
        raw, unit = match.group(1), (match.group(2) or "").lower()
        try:
            val = float(raw.replace(",", ""))
        except ValueError:
            continue
        if unit == "k":
            val *= 1_000
        elif unit in ("lakh", "l"):
            val *= 100_000
        elif unit in ("cr", "crore"):
            val *= 10_000_000
        if abs(val - target) <= tolerance or abs(val - target) / max(abs(target), 1) < 0.005:
            return True
    return False


def _count_sentences(text: str) -> int:
    # Strip markdown tables/lists — they inflate sentence count.
    cleaned = re.sub(r"\|[^\n]*\|", "", text)
    cleaned = re.sub(r"^\s*[-*•]\s", "", cleaned, flags=re.MULTILINE)
    sentences = re.split(r"(?<=[.!?])\s+", cleaned.strip())
    return len([s for s in sentences if s.strip()])


# ---------------------------------------------------------------------------
# The scorer
# ---------------------------------------------------------------------------


def score_response(question: GoldenQuestion, response: Dict[str, Any]) -> ScoreResult:
    """Apply all expect-clauses from a golden question to a TORA response."""
    result = ScoreResult(question_id=question["id"])
    expect = question.get("expect", {})
    text = _extract_text(response)
    text_lc = text.lower()
    mode = _detect_mode(response)
    tools = _tool_names(response)

    # --- Response MUST parse as a dict with some content ---------------
    result.checks.append(CheckResult(
        name="response_non_empty",
        passed=bool(text.strip()),
        detail="" if text.strip() else "Response has no extractable text",
    ))

    # --- Mode ----------------------------------------------------------
    if "mode" in expect:
        expected_mode = expect["mode"]
        result.checks.append(CheckResult(
            name=f"mode=={expected_mode}",
            passed=mode == expected_mode,
            detail=f"got mode={mode}",
        ))

    # --- Tool call expectations ---------------------------------------
    if expect.get("no_tool"):
        result.checks.append(CheckResult(
            name="no_tool_call",
            passed=len(tools) == 0,
            detail=f"unexpected tools: {tools}" if tools else "",
        ))
    if "tool_call" in expect and expect["tool_call"]:
        expected_tool = expect["tool_call"]
        result.checks.append(CheckResult(
            name=f"tool_call=={expected_tool}",
            passed=expected_tool in tools,
            detail=f"got tools={tools}",
        ))

    # --- Must-contain substrings ---------------------------------------
    for needle in expect.get("must_contain", []):
        result.checks.append(CheckResult(
            name=f"contains:{needle!r}",
            passed=needle.lower() in text_lc,
            detail="" if needle.lower() in text_lc else "missing required substring",
        ))

    # --- Must-not-contain ---------------------------------------------
    for needle in expect.get("must_not_contain", []):
        forbidden_present = needle.lower() in text_lc
        result.checks.append(CheckResult(
            name=f"lacks:{needle!r}",
            passed=not forbidden_present,
            detail="forbidden substring present" if forbidden_present else "",
        ))

    # --- Required numbers ---------------------------------------------
    for num in expect.get("must_contain_num", []):
        present = _text_contains_number(text, float(num))
        result.checks.append(CheckResult(
            name=f"number_present:{num}",
            passed=present,
            detail="" if present else f"number {num} not found",
        ))

    # --- Forbidden numbers --------------------------------------------
    for num in expect.get("forbidden_nums", []):
        present = _text_contains_number(text, float(num))
        result.checks.append(CheckResult(
            name=f"number_absent:{num}",
            passed=not present,
            detail="hallucinated number present" if present else "",
        ))

    # --- Length cap ---------------------------------------------------
    if "max_sentences" in expect:
        cap = expect["max_sentences"]
        sc = _count_sentences(text)
        result.checks.append(CheckResult(
            name=f"max_sentences<={cap}",
            passed=sc <= cap,
            detail=f"got {sc} sentences" if sc > cap else "",
        ))

    # --- Ends with a question ----------------------------------------
    if expect.get("should_ask"):
        asks = "?" in text
        result.checks.append(CheckResult(
            name="asks_clarifying_q",
            passed=asks,
            detail="no '?' in reply" if not asks else "",
        ))

    return result


def score_batch(
    questions_and_responses: List[tuple[GoldenQuestion, Dict[str, Any]]],
) -> List[ScoreResult]:
    return [score_response(q, r) for q, r in questions_and_responses]


def aggregate(results: List[ScoreResult]) -> Dict[str, Any]:
    """Roll up a batch of scores into a report dict."""
    total_checks = sum(r.total_count for r in results)
    passed_checks = sum(r.passed_count for r in results)
    perfect = sum(1 for r in results if r.all_passed)
    return {
        "questions_run": len(results),
        "questions_perfect": perfect,
        "checks_passed": passed_checks,
        "checks_total": total_checks,
        "pass_rate": passed_checks / total_checks if total_checks else 0.0,
        "perfect_rate": perfect / len(results) if results else 0.0,
    }
