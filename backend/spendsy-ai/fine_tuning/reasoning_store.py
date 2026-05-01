"""
Reasoning Store — Phase 4 AI trainer loop.

Persists winning traces (score >= 0.75) from the evaluator as JSONL.
Each trace captures the full reasoning chain:
  query, goal_struct, strategies, ranked_output, response, eval_result.

Storage: vault/traces/<YYYY-MM>/<goal_type>.jsonl
  - Monthly rotation — one file per goal type per month.
  - Append-only — never modifies existing traces.
  - Max 10k traces per file; auto-rolls to _2.jsonl, _3.jsonl etc.

Also maintains a hot index (in-memory) for few_shot_injector to query
without reading disk on every request.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

TRACES_DIR = Path(os.path.dirname(__file__)).parent / "vault" / "traces"
MAX_TRACES_PER_FILE = 10_000
_INDEX_LOCK = threading.Lock()

# In-memory hot index: goal_type -> list of trace dicts (last 200 per type)
_hot_index: dict[str, list[dict]] = {}
_HOT_INDEX_MAX = 200


def _trace_path(goal_type: str, month: str) -> Path:
    """vault/traces/YYYY-MM/<goal_type>.jsonl"""
    d = TRACES_DIR / month
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{goal_type}.jsonl"
    # Roll if too large
    idx = 1
    while p.exists() and sum(1 for _ in p.open()) >= MAX_TRACES_PER_FILE:
        idx += 1
        p = d / f"{goal_type}_{idx}.jsonl"
    return p


def save(
    query: str,
    goal_struct: Optional[dict] = None,
    strategies: Optional[list] = None,
    ranked_output: Optional[dict] = None,
    response_text: str = "",
    eval_result=None,
    user_id: Optional[int] = None,
) -> bool:
    """
    Persist a winning trace.

    Args:
        query:         Original user question.
        goal_struct:   GoalStruct.raw_entities dict (serialisable).
        strategies:    List of strategy dicts from financial_reasoner.
        ranked_output: Full rank_strategies() output.
        response_text: TORA's final text response.
        eval_result:   EvalResult dataclass from evaluator.
        user_id:       Anonymised — stored as hash, never raw.

    Returns:
        True if saved successfully.
    """
    try:
        import hashlib
        goal_type = "generic"
        if goal_struct:
            goal_type = goal_struct.get("goal_type", "generic")
        elif eval_result:
            goal_type = getattr(eval_result, "goal_type", "generic")

        month = datetime.now(timezone.utc).strftime("%Y-%m")
        path  = _trace_path(goal_type, month)

        # Anonymise user_id
        uid_hash = hashlib.sha256(str(user_id).encode()).hexdigest()[:12] if user_id else None

        # Tag techniques applied to this trace
        try:
            from agents.tora.reasoning.techniques import tag_techniques
            technique_tag = tag_techniques(query, goal_struct)
        except Exception:
            technique_tag = []

        trace = {
            "saved_at":       datetime.now(timezone.utc).isoformat(),
            "query":          query,
            "goal_type":      goal_type,
            "goal_struct":    goal_struct or {},
            "strategies":     (strategies or [])[:5],          # cap at 5
            "best_strategy":  (ranked_output or {}).get("best", {}),
            "response":       response_text[:500],             # cap for storage
            "eval_score":     getattr(eval_result, "score", None),
            "eval_dims":      getattr(eval_result, "dimensions", {}),
            "technique_tag":  technique_tag,
            "user_id_hash":   uid_hash,
        }

        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trace, ensure_ascii=False) + "\n")

        # Update hot index
        with _INDEX_LOCK:
            if goal_type not in _hot_index:
                _hot_index[goal_type] = []
            _hot_index[goal_type].append(trace)
            if len(_hot_index[goal_type]) > _HOT_INDEX_MAX:
                _hot_index[goal_type] = _hot_index[goal_type][-_HOT_INDEX_MAX:]

        logger.info("reasoning_store: saved trace goal=%s score=%.3f path=%s",
                    goal_type, trace.get("eval_score", 0), path.name)
        return True

    except Exception as exc:
        logger.error("reasoning_store save failed: %s", exc)
        return False


def load_traces(
    goal_type: str,
    limit: int = 50,
    min_score: float = 0.75,
) -> list[dict]:
    """
    Load recent winning traces for a goal type.
    Checks hot index first (fast), falls back to disk scan.
    """
    # Hot index
    with _INDEX_LOCK:
        hot = list(_hot_index.get(goal_type, []))
    if hot:
        filtered = [t for t in hot if (t.get("eval_score") or 0) >= min_score]
        return filtered[-limit:]

    # Disk fallback — read latest monthly file
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    path = TRACES_DIR / month / f"{goal_type}.jsonl"
    if not path.exists():
        return []

    traces = []
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    t = json.loads(line)
                    if (t.get("eval_score") or 0) >= min_score:
                        traces.append(t)
                except json.JSONDecodeError:
                    continue
    except Exception as exc:
        logger.warning("reasoning_store load failed: %s", exc)

    return traces[-limit:]


def get_index_stats() -> dict:
    """Summary of hot index for monitoring."""
    with _INDEX_LOCK:
        return {
            goal: len(traces)
            for goal, traces in _hot_index.items()
        }
