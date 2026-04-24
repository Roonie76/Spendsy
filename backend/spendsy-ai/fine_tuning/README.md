# TORA Fine-Tuning Pipeline

This directory contains the scaffolding for fine-tuning TORA's local models
(Gemma 4 E2B / LLaMA-3) on real user interactions.

## Pipeline Stages

```
1. Data Collection  →  2. Export & Format  →  3. Train  →  4. Evaluate
   (collect.py)         (export.py)           (TBD)       (eval_harness.py)
```

### 1. Data Collection (`collect.py`)
- Reads thumbs-up conversations from `ToraFeedback` + `ToraConversation` tables
- Filters to high-quality assistant turns (rating = 'up', structured response present)
- Outputs JSONL with `{system, user, assistant}` triplets

### 2. Export & Format (`export.py`)
- Converts collected JSONL into model-specific formats:
  - **Gemma**: `<start_of_turn>user\n...<end_of_turn><start_of_turn>model\n...<end_of_turn>`
  - **LLaMA**: `[INST] ... [/INST]`
  - **OpenAI-compatible**: `{"messages": [...]}`
- Train/val split (90/10)
- Token count estimation and budget warnings

### 3. Train (TBD)
- Not yet implemented. Will use either:
  - `unsloth` for local LoRA fine-tuning
  - Hugging Face `trl` SFTTrainer
  - OpenAI fine-tuning API (for hosted models)

### 4. Evaluate
- **Golden-question test set**: LLM-inclusive checks for mode correctness and accuracy.
- **Stress Harness**: 1200-query deterministic benchmark for intent resolution across English, Hinglish, and Typos.
- **Run with**:
  - `python -m pytest tests/eval/ -v` (Golden questions)
  - `python -m tests.tora_eval.stress.simulate --n 1200` (Stress harness)

## Directory Structure

```
fine_tuning/
├── README.md          ← You are here
├── collect.py         ← Data collection from production DB
├── export.py          ← Format conversion for training
└── data/              ← Generated datasets (gitignored)
    ├── raw/           ← Raw JSONL from collect.py
    └── formatted/     ← Model-specific formats from export.py
```

## Quick Start

```bash
# Collect positive-rated conversations
python fine_tuning/collect.py --min-rating up --limit 5000

# Export to Gemma chat format
python fine_tuning/export.py --format gemma --output data/formatted/gemma_train.jsonl
```

## Requirements

- Access to the finance-service database (or internal API)
- Python 3.11+
- No additional dependencies beyond the base `spendsy-ai` requirements
