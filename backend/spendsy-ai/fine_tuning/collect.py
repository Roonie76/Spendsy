"""collect.py — Extract high-quality TORA conversations for fine-tuning.

Reads from the finance-service internal API to pull conversations where the
user gave a thumbs-up, then packages them as {system, user, assistant}
triplets suitable for supervised fine-tuning.

Usage:
    python fine_tuning/collect.py --min-rating up --limit 5000 --output data/raw/positive.jsonl
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys

# Ensure parent dir is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings  # noqa: E402

logger = logging.getLogger(__name__)


def fetch_feedback_rows(min_rating: str = "up", limit: int = 5000) -> list[dict]:
    """Fetch feedback rows from finance-service internal API.

    Returns a list of dicts with keys:
        user_id, message_id, client_message_id, rating, prompt, response_preview
    """
    import urllib.request
    import urllib.error

    url = (
        f"{settings.finance_service_url}/internal/tora-feedback/aggregate"
        f"?days=90"
    )
    headers = {
        "X-Internal-API-Key": settings.internal_api_key,
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("data", [])
    except Exception as e:
        logger.error(f"Failed to fetch feedback: {e}")
        return []


def fetch_conversation_for_user(user_id: int, limit: int = 100) -> list[dict]:
    """Fetch conversation history for a specific user."""
    import urllib.request

    url = (
        f"{settings.finance_service_url}/internal/tora-conversation/{user_id}"
        f"?limit={limit}"
    )
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("data", [])
    except Exception:
        return []


def build_training_triplets(
    conversations: list[dict],
    system_prompt: str | None = None,
) -> list[dict]:
    """Convert conversation turns into training triplets.

    Each triplet contains:
        system: The TORA system prompt
        user: The user's question
        assistant: TORA's response
    """
    if system_prompt is None:
        from agents.tora_personality import TORA_SYSTEM_PROMPT
        system_prompt = TORA_SYSTEM_PROMPT

    triplets: list[dict] = []
    i = 0
    while i < len(conversations) - 1:
        user_turn = conversations[i]
        assistant_turn = conversations[i + 1]

        if user_turn.get("role") == "user" and assistant_turn.get("role") == "assistant":
            triplets.append({
                "system": system_prompt[:2000],  # Truncate for training
                "user": user_turn.get("content", ""),
                "assistant": assistant_turn.get("content", ""),
            })
            i += 2
        else:
            i += 1

    return triplets


def main():
    parser = argparse.ArgumentParser(description="Collect TORA fine-tuning data")
    parser.add_argument("--min-rating", default="up", choices=["up", "down"])
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--output", default="fine_tuning/data/raw/positive.jsonl")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # TODO: Implement full pipeline once ToraFeedback has enough production data.
    # For now, this stub validates the import chain and CLI interface.
    logger.info(
        f"Collection stub: would fetch {args.limit} rows with "
        f"min_rating={args.min_rating} and write to {args.output}"
    )
    print(f"[stub] Output would be written to: {args.output}")
    print("[stub] Implement fetch_feedback_rows + per-user conversation join.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
