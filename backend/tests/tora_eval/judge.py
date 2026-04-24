"""LLM judge for soft quality grading of TORA responses.

Pairs with the deterministic `scorer.py` — the scorer catches hard failures
(wrong number, wrong mode, fabricated figures), the judge grades the soft
qualities: clarity, tone, honesty, user-respecting behavior.

The judge is scaffolded to be pluggable:

    JUDGE_MODEL = "qwen2.5:7b"      # any non-Gemma Ollama model
    enabled = JUDGE_MODEL installed in your local Ollama

If the configured judge model isn't installed, `judge_response` returns a
neutral "skipped" result — the harness still runs with rule-based checks
only. Install any non-Gemma model to activate:

    ollama pull qwen2.5:7b          # recommended
    ollama pull llama3:8b           # alternative

Rationale: using Gemma to judge Gemma creates grading-your-own-homework
bias. An independent model family (Qwen, LLaMA, Mistral) is required.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .golden_questions import GoldenQuestion

logger = logging.getLogger(__name__)


JUDGE_MODEL = os.getenv("TORA_EVAL_JUDGE_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


# ---------------------------------------------------------------------------
# Judge prompt — constrained rubric so scores are comparable across runs.
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """You are an impartial evaluator grading a financial assistant's reply.

Grade the reply against the user question on each dimension below, 0–5:

  - clarity: Is the reply easy to read and structured appropriately?
  - tone: Is it direct, respectful, non-preachy, non-sycophantic?
  - honesty: Does it avoid fabricated numbers, admit when data is missing, label estimates?
  - helpfulness: Does it actually solve the user's problem (not just say words)?
  - persona_fit: Does it sound like a competent senior financial engineer, not a chatbot?

Return a JSON object exactly in this shape:

{"clarity":N,"tone":N,"honesty":N,"helpfulness":N,"persona_fit":N,"note":"<=25 word critique"}

No markdown fences. No extra keys. Integers 0–5 only."""


@dataclass
class JudgeResult:
    question_id: str
    enabled: bool
    scores: Dict[str, int] = field(default_factory=dict)
    note: str = ""
    error: str = ""

    @property
    def average(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores.values()) / len(self.scores)

    @property
    def out_of_5(self) -> float:
        return self.average

    @property
    def normalized(self) -> float:
        """0–1 score for combining with rule-based scorer."""
        return self.average / 5.0 if self.scores else 0.0


# ---------------------------------------------------------------------------
# Model availability check
# ---------------------------------------------------------------------------


def _judge_available() -> bool:
    """Quick liveness check — is the judge model installed locally?"""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=2) as r:
            data = json.loads(r.read().decode("utf-8"))
            names = {m.get("name", "") for m in data.get("models", [])}
            # Accept exact match or `name:tag` prefix
            base = JUDGE_MODEL.split(":")[0]
            return any(n == JUDGE_MODEL or n.startswith(f"{base}:") for n in names)
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        return False


# ---------------------------------------------------------------------------
# Judge invocation
# ---------------------------------------------------------------------------


def _format_response_for_judge(response: Dict[str, Any]) -> str:
    """Produce the text the judge will read as 'the assistant's reply'."""
    if not isinstance(response, dict):
        return str(response)
    if response.get("mode") == "simple":
        return str(response.get("content", "")).strip()
    lines: List[str] = []
    for key in ("Financial Overview", "Current Position", "Recommended Strategy", "Expected Outcome"):
        v = response.get(key)
        if v:
            lines.append(f"{key}: {v}")
    tools = response.get("tool_calls") or []
    if tools:
        lines.append(f"[tool_calls: {', '.join(t.get('name','?') for t in tools)}]")
    return "\n".join(lines).strip()


def judge_response(question: GoldenQuestion, response: Dict[str, Any]) -> JudgeResult:
    """Call the judge model and parse its rubric JSON."""
    qid = question["id"]

    if not _judge_available():
        return JudgeResult(
            question_id=qid,
            enabled=False,
            error=f"judge model {JUDGE_MODEL!r} not installed in local Ollama — skipped",
        )

    assistant_text = _format_response_for_judge(response)
    user_prompt = (
        f"USER QUESTION:\n{question['prompt']}\n\n"
        f"ASSISTANT REPLY:\n{assistant_text}\n\n"
        "Grade on all five dimensions and return the JSON object."
    )

    payload = {
        "model": JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "num_ctx": 4096, "num_predict": 256, "seed": 7},
    }

    try:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read().decode("utf-8"))
        content = body.get("message", {}).get("content", "").strip()
        parsed = json.loads(content)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return JudgeResult(question_id=qid, enabled=True, error=f"judge transport error: {e}")
    except json.JSONDecodeError as e:
        return JudgeResult(question_id=qid, enabled=True, error=f"judge returned non-JSON: {e}")

    scores: Dict[str, int] = {}
    for dim in ("clarity", "tone", "honesty", "helpfulness", "persona_fit"):
        raw = parsed.get(dim)
        if isinstance(raw, (int, float)) and 0 <= raw <= 5:
            scores[dim] = int(raw)

    if not scores:
        return JudgeResult(
            question_id=qid,
            enabled=True,
            error=f"judge response missing rubric keys: {parsed}",
        )

    return JudgeResult(
        question_id=qid,
        enabled=True,
        scores=scores,
        note=str(parsed.get("note", ""))[:200],
    )
