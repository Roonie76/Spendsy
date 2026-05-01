"""
Seed Traces — Phase 5.

Hardcoded high-quality reasoning traces from the training spec diagram.
These are injected into the hot index on first import so few_shot_injector
has examples even before any live traces accumulate.

Each trace follows the reasoning_store schema:
  query, goal_type, best_strategy, response, eval_score,
  technique_tag, reasoning_chain, why_it_matters
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed data (verbatim from spec diagram, with structured reasoning chain)
# ---------------------------------------------------------------------------

SEED_TRACES: list[dict] = [
    {
        "query": "I have ₹2L credit card debt at 36% interest and I want to buy a car for ₹8L.",
        "goal_type": "car",
        "technique_tag": ["second_order", "first_principles"],
        "reasoning_chain": (
            "Surface answer: take a car loan for ₹8L. "
            "Second-order trace: CC debt at 36% costs ₹6,000/month in interest. "
            "Consolidate CC debt into personal loan @ 14% → saves ₹1,833/month interest. "
            "Redeploy savings toward car down payment → reduces car loan principal. "
            "Lower principal → EMI drops by ~₹2,100/month. "
            "Net monthly outflow is actually LOWER than taking a car loan alone."
        ),
        "why_it_matters": "Solving adjacent problems first unlocks the primary goal cheaper.",
        "best_strategy": {
            "name": "CC Consolidation + Stepped Car Purchase",
            "steps": [
                "Take personal loan at 14% to clear CC debt",
                "Save ₹1,833/month freed interest for 6 months (₹11K down)",
                "Then apply for reduced car loan",
            ],
            "total_cost_inr": 760000,
            "monthly_outflow_inr": 18500,
        },
        "response": (
            "Before buying the car, clear your ₹2L CC debt first. "
            "A personal loan at 14% saves ₹1,833/month vs the 36% card. "
            "After 6 months of saving that freed cash, your car loan EMI drops by ~₹2,100. "
            "Net result: you own the car and pay LESS per month than if you'd taken the car loan today."
        ),
        "eval_score": 0.92,
        "eval_dims": {
            "goal_addressed": 0.95,
            "numbers_audited": 0.90,
            "compliance": 1.0,
            "user_feedback": 0.85,
        },
        "saved_at": "2026-01-15T10:00:00+00:00",
        "user_id_hash": "seed_000000000001",
        "goal_struct": {
            "goal_type": "car",
            "amount_inr": 800000,
            "constraints": ["existing CC debt at 36%"],
        },
        "strategies": [],
    },
    {
        "query": "I am 26 years old and want to invest but have no savings.",
        "goal_type": "invest",
        "technique_tag": ["reframing", "first_principles"],
        "reasoning_chain": (
            "Surface answer: start a SIP. "
            "Reframing: the question is not 'how to save more' but 'where is money already leaking?' "
            "Audit subscriptions → identify ₹3,400/month in unused/duplicate subscriptions. "
            "Redirect ₹3,400 to SIP → at 12% CAGR for 30 years = ₹1.06 Crore. "
            "The money already existed — it was misrouted."
        ),
        "why_it_matters": "Reframing from 'how to save more' to 'where is money already leaking'.",
        "best_strategy": {
            "name": "Subscription Audit + Auto-SIP Redirect",
            "steps": [
                "Audit last 3 months transactions for recurring charges",
                "Cancel unused subscriptions (target ₹3,400/month)",
                "Auto-debit SIP on salary day",
            ],
            "total_cost_inr": 0,
            "monthly_outflow_inr": 3400,
        },
        "response": (
            "You don't need new income to invest — you need to redirect what's leaking. "
            "An audit of your last 3 months shows ~₹3,400/month in subscriptions you may not use. "
            "Cancel duplicates, set up an auto-SIP on salary day. "
            "₹3,400/month at 12% CAGR for 30 years = ₹1.06 Crore. The money already existed."
        ),
        "eval_score": 0.91,
        "eval_dims": {
            "goal_addressed": 0.90,
            "numbers_audited": 0.95,
            "compliance": 1.0,
            "user_feedback": 0.88,
        },
        "saved_at": "2026-01-20T10:00:00+00:00",
        "user_id_hash": "seed_000000000002",
        "goal_struct": {
            "goal_type": "invest",
            "amount_inr": None,
            "constraints": ["no current savings"],
        },
        "strategies": [],
    },
    {
        "query": "I am in high-interest debt and my credit score is not improving.",
        "goal_type": "loan_repay",
        "technique_tag": ["second_order", "constraint_relax"],
        "reasoning_chain": (
            "Surface answer: pay minimum due. "
            "Second-order: identify smallest debt → pay off fully using avalanche+snowball hybrid. "
            "Each closure event raises credit score (CIBIL score improvement per closed account). "
            "New higher score unlocks lower-rate refinancing. "
            "Refinance remaining debt at lower rate → total interest saved: 38% vs minimum-due path. "
            "Non-linear sequencing — order of operations matters as much as the operations."
        ),
        "why_it_matters": "Non-linear sequencing — order of operations matters as much as the operations themselves.",
        "best_strategy": {
            "name": "Avalanche-Snowball Hybrid + Credit-Unlock Refinance",
            "steps": [
                "List all debts by balance (smallest first) and rate (highest first)",
                "Attack smallest balance to closure → credit score event",
                "Attack highest rate next with freed cash",
                "After 2 closures, apply for refinance at lower rate",
            ],
            "total_cost_inr": None,
            "monthly_outflow_inr": None,
        },
        "response": (
            "Minimum payments trap you. Here's a sequenced exit: "
            "1) Pay off your smallest debt fully — each closure boosts your CIBIL score. "
            "2) With a higher score, refinance remaining debt at a lower rate. "
            "3) Apply the avalanche method (highest rate next) on the restructured balance. "
            "Total interest saved vs minimum-due path: ~38%."
        ),
        "eval_score": 0.89,
        "eval_dims": {
            "goal_addressed": 0.90,
            "numbers_audited": 0.85,
            "compliance": 1.0,
            "user_feedback": 0.90,
        },
        "saved_at": "2026-02-01T10:00:00+00:00",
        "user_id_hash": "seed_000000000003",
        "goal_struct": {
            "goal_type": "loan_repay",
            "amount_inr": None,
            "constraints": ["high interest debt", "low credit score"],
        },
        "strategies": [],
    },
    {
        "query": "I want a home loan but my income is irregular as a freelancer.",
        "goal_type": "house",
        "technique_tag": ["constraint_relax", "reframing"],
        "reasoning_chain": (
            "Surface answer: you may not qualify. "
            "Constraint relaxation: the constraint is 'regular income proof' — what if we redefine it? "
            "Aggregate 24-month bank statement average → shows consistent income pattern. "
            "Approach co-lending platform (not traditional bank) → different underwriting model. "
            "Pair with a co-applicant → qualify for 80% LTV. "
            "Constraint: irregular income. Relaxation: redefine 'income proof'."
        ),
        "why_it_matters": "Constraint relaxation — question the definition, not just the value.",
        "best_strategy": {
            "name": "24-Month Average + Co-Lending + Co-Applicant",
            "steps": [
                "Compile 24-month bank statements showing consistent deposits",
                "Approach co-lending platforms (Piramal, Tata Capital, etc.)",
                "Add co-applicant with salaried income for better LTV",
                "Target 80% LTV on property valuation",
            ],
            "total_cost_inr": None,
            "monthly_outflow_inr": None,
        },
        "response": (
            "Irregular income doesn't disqualify you — it just requires a different approach. "
            "Step 1: Compile 24 months of bank statements; the average deposit is your 'income'. "
            "Step 2: Approach co-lending platforms (Piramal, Tata Capital) — they use ITR + bank statement underwriting. "
            "Step 3: Add a co-applicant with salaried income to qualify for 80% LTV. "
            "You can likely secure a home loan — just not from a traditional bank's standard branch."
        ),
        "eval_score": 0.90,
        "eval_dims": {
            "goal_addressed": 0.92,
            "numbers_audited": 0.80,
            "compliance": 1.0,
            "user_feedback": 0.88,
        },
        "saved_at": "2026-02-10T10:00:00+00:00",
        "user_id_hash": "seed_000000000004",
        "goal_struct": {
            "goal_type": "house",
            "amount_inr": None,
            "constraints": ["freelancer", "irregular income"],
        },
        "strategies": [],
    },
]


# ---------------------------------------------------------------------------
# Loader — call once on startup
# ---------------------------------------------------------------------------

def load_seed_traces() -> int:
    """
    Inject seed traces into reasoning_store's hot index.
    Returns the number of traces loaded (0 if already loaded or error).
    """
    try:
        from fine_tuning.reasoning_store import _hot_index, _INDEX_LOCK, _HOT_INDEX_MAX
        import threading

        loaded = 0
        with _INDEX_LOCK:
            for trace in SEED_TRACES:
                gt = trace.get("goal_type", "generic")
                # Only inject if not already present (avoid re-seeding on restart)
                existing = _hot_index.get(gt, [])
                already = any(
                    t.get("user_id_hash", "").startswith("seed_")
                    for t in existing
                )
                if not already:
                    if gt not in _hot_index:
                        _hot_index[gt] = []
                    _hot_index[gt].insert(0, trace)  # prepend so recency sort keeps live traces on top
                    if len(_hot_index[gt]) > _HOT_INDEX_MAX:
                        _hot_index[gt] = _hot_index[gt][-_HOT_INDEX_MAX:]
                    loaded += 1

        if loaded:
            logger.info("seed_traces: loaded %d seed traces into hot index", loaded)
        return loaded

    except Exception as exc:
        logger.warning("seed_traces: failed to load seeds: %s", exc)
        return 0
