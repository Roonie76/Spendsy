"""export.py — Convert collected TORA training data into model-specific formats.

Takes raw JSONL triplets from collect.py and reformats them for:
  - Gemma chat template
  - LLaMA instruct template
  - OpenAI fine-tuning API format

Usage:
    python fine_tuning/export.py --format gemma --input data/raw/positive.jsonl --output data/formatted/gemma_train.jsonl
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys

logger = logging.getLogger(__name__)

FORMATS = ("gemma", "llama", "openai")


def to_gemma(triplet: dict) -> str:
    """Convert to Gemma chat template."""
    system = triplet.get("system", "")
    user = triplet.get("user", "")
    assistant = triplet.get("assistant", "")
    return (
        f"<start_of_turn>user\n{system}\n\n{user}<end_of_turn>\n"
        f"<start_of_turn>model\n{assistant}<end_of_turn>"
    )


def to_llama(triplet: dict) -> dict:
    """Convert to LLaMA instruct format."""
    system = triplet.get("system", "")
    user = triplet.get("user", "")
    assistant = triplet.get("assistant", "")
    return {
        "text": f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST] {assistant} </s>"
    }


def to_openai(triplet: dict) -> dict:
    """Convert to OpenAI fine-tuning format."""
    return {
        "messages": [
            {"role": "system", "content": triplet.get("system", "")},
            {"role": "user", "content": triplet.get("user", "")},
            {"role": "assistant", "content": triplet.get("assistant", "")},
        ]
    }


FORMAT_CONVERTERS = {
    "gemma": to_gemma,
    "llama": to_llama,
    "openai": to_openai,
}


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for English text."""
    return len(text) // 4


def main():
    parser = argparse.ArgumentParser(description="Export TORA training data")
    parser.add_argument("--format", choices=FORMATS, default="gemma")
    parser.add_argument("--input", default="fine_tuning/data/raw/positive.jsonl")
    parser.add_argument("--output", default=None, help="Output path (auto-generated if omitted)")
    parser.add_argument("--val-split", type=float, default=0.1, help="Validation split ratio")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.output is None:
        args.output = f"fine_tuning/data/formatted/{args.format}_train.jsonl"

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Load raw data
    if not os.path.exists(args.input):
        print(f"[stub] Input file not found: {args.input}")
        print("[stub] Run collect.py first to generate raw training data.")
        return

    with open(args.input, "r") as f:
        triplets = [json.loads(line) for line in f if line.strip()]

    if not triplets:
        print("[stub] No training data found.")
        return

    random.seed(args.seed)
    random.shuffle(triplets)

    converter = FORMAT_CONVERTERS[args.format]
    split_idx = max(1, int(len(triplets) * (1 - args.val_split)))
    train_set = triplets[:split_idx]
    val_set = triplets[split_idx:]

    # Write train
    total_tokens = 0
    with open(args.output, "w") as f:
        for t in train_set:
            converted = converter(t)
            line = json.dumps(converted) if isinstance(converted, dict) else json.dumps({"text": converted})
            f.write(line + "\n")
            total_tokens += estimate_tokens(str(converted))

    # Write val
    val_output = args.output.replace("_train.", "_val.")
    with open(val_output, "w") as f:
        for t in val_set:
            converted = converter(t)
            line = json.dumps(converted) if isinstance(converted, dict) else json.dumps({"text": converted})
            f.write(line + "\n")

    print(f"Exported {len(train_set)} train + {len(val_set)} val examples")
    print(f"Estimated tokens: ~{total_tokens:,}")
    print(f"Train: {args.output}")
    print(f"Val:   {val_output}")

    # Budget warning
    if total_tokens > 500_000:
        print(f"\n⚠️  Token count ({total_tokens:,}) exceeds 500K — may be expensive for API fine-tuning.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
