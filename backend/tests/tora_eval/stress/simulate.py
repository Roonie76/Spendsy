"""Run the generated query corpus through the TORA Universal Intelligence Engine.

Records per-query outcomes to JSONL for offline analysis. Does NOT call the
LLM — the point is to stress-test the pre-LLM layer (resolver, engine,
context builder, thinking gate) where issues are cheap to find and fix.

Usage:
    cd backend && python -m tests.tora_eval.stress.simulate \\
        --n 1200 --out stress_results.jsonl --seed 42
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Make the spendsy-ai package importable.
_SPENDSY_AI_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "spendsy-ai")
)
if _SPENDSY_AI_DIR not in sys.path:
    sys.path.insert(0, _SPENDSY_AI_DIR)

from agents.tora import (  # noqa: E402
    resolve_and_fetch,
    build_market_context_block,
    should_enable_thinking,
    summarize_fetch_outcome,
)

from .query_generator import GeneratedQuery, generate_corpus, summarize_corpus

logger = logging.getLogger(__name__)


async def _run_one(q: GeneratedQuery) -> dict[str, Any]:
    """Run a single query through the engine and record outcomes.

    We capture enough per-query detail that the report can surface
    actionable errors — the generated resolver output, context block
    size, thinking decision, latency, and ground-truth labels.
    """
    t0 = time.perf_counter()
    try:
        fetch_results = await resolve_and_fetch(
            q.text, user_surplus=float(q.persona.monthly_surplus)
        )
    except Exception as e:
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "text": q.text,
            "persona": q.persona.name,
            "label": {
                "track": q.label.track,
                "expected_plugin": q.label.expected_plugin,
                "category_tag": q.label.category_tag,
                "style": q.label.style,
                "should_enable_thinking": q.label.should_enable_thinking,
            },
            "error": f"{type(e).__name__}: {e}",
            "elapsed_ms": round(elapsed_ms, 2),
            "matched_plugins": [],
            "thinking_enabled": False,
            "block_chars": 0,
            "block_tokens_approx": 0,
        }

    block = build_market_context_block(fetch_results) if fetch_results else ""
    thinking = should_enable_thinking(q.text, has_plugin_match=bool(block))
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    summary = summarize_fetch_outcome(fetch_results)

    return {
        "text": q.text,
        "persona": q.persona.name,
        "label": {
            "track": q.label.track,
            "expected_plugin": q.label.expected_plugin,
            "category_tag": q.label.category_tag,
            "style": q.label.style,
            "should_enable_thinking": q.label.should_enable_thinking,
        },
        "elapsed_ms": round(elapsed_ms, 2),
        "matched_plugins": [
            {
                "plugin_id": p["plugin_id"],
                "entity": p["entity"],
                "role": p["role"],
                "score": p["score"],
                "strategy": p["strategy"],
                "any_live_used": p["any_live_used"],
                "fact_count": p["fact_count"],
            }
            for p in summary["plugins"]
        ],
        "thinking_enabled": thinking,
        "block_chars": len(block),
        "block_tokens_approx": len(block) // 4,
    }


async def run_corpus(
    corpus: list[GeneratedQuery], concurrency: int = 20
) -> list[dict[str, Any]]:
    """Run every query, bounded by `concurrency` concurrent coroutines.

    The engine itself fans out plugin fetches internally; adding outer
    concurrency just speeds up the sweep over the corpus.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def _guarded(q: GeneratedQuery) -> dict[str, Any]:
        async with semaphore:
            return await _run_one(q)

    return await asyncio.gather(*(_guarded(q) for q in corpus))


def write_jsonl(path: Path, header: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    """First line is a header row with corpus metadata; subsequent lines
    are per-query results. Readers can split on the header key."""
    with path.open("w", encoding="utf-8") as fh:
        fh.write(json.dumps({"__header__": True, **header}) + "\n")
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="TORA engine stress test")
    parser.add_argument("--n", type=int, default=1200, help="target corpus size")
    parser.add_argument("--seed", type=int, default=42, help="deterministic seed")
    parser.add_argument(
        "--out",
        type=str,
        default="stress_results.jsonl",
        help="output JSONL path",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=20,
        help="concurrent engine calls in flight",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s"
    )

    corpus = generate_corpus(n_target=args.n, seed=args.seed)
    corpus_summary = summarize_corpus(corpus)
    print(f"Generated {len(corpus)} queries. Breakdown: {json.dumps(corpus_summary)}")

    t0 = time.perf_counter()
    rows = asyncio.run(run_corpus(corpus, concurrency=args.concurrency))
    total_elapsed = time.perf_counter() - t0

    out_path = Path(args.out).resolve()
    write_jsonl(
        out_path,
        header={
            "corpus_summary": corpus_summary,
            "seed": args.seed,
            "total_elapsed_seconds": round(total_elapsed, 2),
            "concurrency": args.concurrency,
        },
        rows=rows,
    )
    print(
        f"Wrote {len(rows)} results to {out_path} in {total_elapsed:.1f}s "
        f"(~{total_elapsed / max(1, len(rows)) * 1000:.1f}ms/query)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
