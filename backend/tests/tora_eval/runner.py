"""TORA eval harness runner.

Exercises the full agent pipeline (build_ai_context → LLM → post-processing)
against each golden question with the MCP fetch and DB writes stubbed out.

Usage:

    # Full run with rule-based scoring + LLM judge (if installed)
    python -m tests.tora_eval.runner

    # Only a subset of questions
    python -m tests.tora_eval.runner --ids lookup_balance,plan_laptop

    # Skip the LLM judge (rule-based only, offline)
    python -m tests.tora_eval.runner --no-judge

    # Write JSON report
    python -m tests.tora_eval.runner --out eval_report.json

The runner is idempotent and uses deterministic fixtures, so it's safe to
run repeatedly and diff reports across prompt revisions.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

# Make the spendsy-ai package importable (folder contains a hyphen).
_SPENDSY_AI_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "spendsy-ai")
)
if _SPENDSY_AI_DIR not in sys.path:
    sys.path.insert(0, _SPENDSY_AI_DIR)

from .golden_questions import GOLDEN_QUESTIONS, GoldenQuestion  # noqa: E402
from .judge import judge_response, JudgeResult  # noqa: E402
from .scorer import aggregate, score_response, ScoreResult  # noqa: E402

logger = logging.getLogger("tora_eval.runner")


# ---------------------------------------------------------------------------
# Pipeline stubbing — keep the real agent code on the hot path, but cut out
# network / DB dependencies that would make evals flaky or slow.
# ---------------------------------------------------------------------------


@contextmanager
def stubbed_agent(fixture: Dict[str, Any], history: List[Dict[str, str]]):
    """Patch MCP fetch, conversation load/save, and tool execution for evals."""
    import agents.tora_agent as ta  # local import after sys.path tweak

    async def _fake_fetch(user_id: int) -> Dict[str, Any]:
        return fixture

    def _fake_load(user_id: int, user_tier: str = "free") -> List[Dict[str, Any]]:
        return list(history)

    def _fake_save(*args, **kwargs) -> None:
        return None

    # We intentionally let call_llm run for real — that's the whole point.
    # We also let build_ai_context, _rupee_ize, mode detection, etc. run.
    with patch.object(ta, "fetch_financial_summary", new=_fake_fetch), \
         patch.object(ta, "_load_recent_conversation", new=_fake_load), \
         patch.object(ta, "_save_conversation", new=_fake_save), \
         patch.object(ta, "get_tool_registry", return_value={}):  # suppress real tool execution
        yield ta


async def _run_one(question: GoldenQuestion, tier: str = "pro") -> Dict[str, Any]:
    """Run TORA against a single golden question and return its response."""
    fixture = question.get("fixture", {})
    history = question.get("history", [])
    with stubbed_agent(fixture, history) as ta:
        return await ta.handle_user_question(
            user_id=9999,  # Fake — fetch is stubbed
            question=question["prompt"],
            model="tora",
            user_tier=tier,
        )


# ---------------------------------------------------------------------------
# Batch orchestration
# ---------------------------------------------------------------------------


def _select(ids: List[str] | None) -> List[GoldenQuestion]:
    if not ids:
        return list(GOLDEN_QUESTIONS)
    wanted = set(ids)
    picked = [q for q in GOLDEN_QUESTIONS if q["id"] in wanted]
    missing = wanted - {q["id"] for q in picked}
    if missing:
        raise SystemExit(f"Unknown question ids: {sorted(missing)}")
    return picked


async def run_all(
    ids: List[str] | None = None,
    use_judge: bool = True,
    tier: str = "pro",
) -> Dict[str, Any]:
    questions = _select(ids)
    responses: List[Tuple[GoldenQuestion, Dict[str, Any]]] = []
    latencies: List[float] = []

    for i, q in enumerate(questions, 1):
        logger.info("[%d/%d] %s", i, len(questions), q["id"])
        start = time.time()
        try:
            resp = await _run_one(q, tier=tier)
        except Exception as e:
            logger.error("crash on %s: %s", q["id"], e)
            resp = {"mode": "simple", "content": f"[runner error: {e}]", "_runner_error": str(e)}
        latencies.append(time.time() - start)
        responses.append((q, resp))

    rule_results: List[ScoreResult] = [score_response(q, r) for q, r in responses]
    judge_results: List[JudgeResult] = []
    if use_judge:
        for q, r in responses:
            judge_results.append(judge_response(q, r))
    else:
        judge_results = [JudgeResult(question_id=q["id"], enabled=False, error="judge disabled by flag") for q, _ in responses]

    return _build_report(questions, responses, rule_results, judge_results, latencies)


def _build_report(
    questions: List[GoldenQuestion],
    responses: List[Tuple[GoldenQuestion, Dict[str, Any]]],
    rule_results: List[ScoreResult],
    judge_results: List[JudgeResult],
    latencies: List[float],
) -> Dict[str, Any]:
    per_question = []
    for (q, resp), rule, judge in zip(responses, rule_results, judge_results):
        per_question.append({
            "id": q["id"],
            "prompt": q["prompt"],
            "response": resp,
            "rule": {
                "score": round(rule.score, 3),
                "passed": rule.passed_count,
                "total": rule.total_count,
                "failures": [{"name": c.name, "detail": c.detail} for c in rule.failures()],
            },
            "judge": {
                "enabled": judge.enabled,
                "normalized": round(judge.normalized, 3),
                "scores": judge.scores,
                "note": judge.note,
                "error": judge.error,
            },
        })

    rule_summary = aggregate(rule_results)
    enabled_judges = [j for j in judge_results if j.enabled and j.scores]
    judge_avg = (
        sum(j.average for j in enabled_judges) / len(enabled_judges)
        if enabled_judges else None
    )
    return {
        "summary": {
            "questions": len(questions),
            "rule": rule_summary,
            "judge": {
                "enabled_count": len(enabled_judges),
                "average_out_of_5": round(judge_avg, 2) if judge_avg is not None else None,
            },
            "latency": {
                "avg_s": round(sum(latencies) / len(latencies), 2) if latencies else 0,
                "max_s": round(max(latencies), 2) if latencies else 0,
            },
        },
        "questions": per_question,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_table(report: Dict[str, Any]) -> None:
    s = report["summary"]
    print("\n=== TORA EVAL REPORT ===")
    print(f"Questions run:        {s['questions']}")
    print(f"Rule pass rate:       {s['rule']['pass_rate']:.1%} "
          f"({s['rule']['checks_passed']}/{s['rule']['checks_total']} checks)")
    print(f"Perfect questions:    {s['rule']['questions_perfect']}/{s['questions']}")
    if s["judge"]["enabled_count"]:
        print(f"Judge score avg:      {s['judge']['average_out_of_5']}/5  "
              f"(from {s['judge']['enabled_count']} graded)")
    else:
        print("Judge score avg:      (judge disabled / model not installed)")
    print(f"Avg latency:          {s['latency']['avg_s']}s  (max {s['latency']['max_s']}s)")

    failed = [q for q in report["questions"] if q["rule"]["failures"]]
    if failed:
        print(f"\n--- {len(failed)} questions with failing rule checks ---")
        for q in failed[:20]:
            print(f"  • {q['id']}  ({q['rule']['passed']}/{q['rule']['total']} passed)")
            for f in q["rule"]["failures"][:3]:
                print(f"      ✗ {f['name']}  {('— ' + f['detail']) if f['detail'] else ''}")
        if len(failed) > 20:
            print(f"  ... and {len(failed) - 20} more")
    else:
        print("\nAll rule checks passed. 🎯  (no emoji in TORA's own replies, of course.)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", type=str, default="", help="Comma-separated question IDs to run")
    parser.add_argument("--no-judge", action="store_true", help="Skip LLM-judge grading")
    parser.add_argument("--tier", type=str, default="pro", help="User tier to simulate (free|pro|enterprise)")
    parser.add_argument("--out", type=str, default="", help="Write full report to this JSON file")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    ids = [s.strip() for s in args.ids.split(",") if s.strip()] or None
    report = asyncio.run(run_all(ids=ids, use_judge=not args.no_judge, tier=args.tier))
    _print_table(report)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        print(f"\nFull report written to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
