"""
Strategy Ranker — Phase 3.

Scores each strategy from financial_reasoner on 5 dimensions,
computes weighted composite score, returns ranked list with recommendation.

Dimensions (weights sum to 1.0):
  total_cost_efficiency  0.30  — lower total cost = higher score
  cash_flow_impact       0.25  — lower monthly outflow relative to surplus
  feasibility            0.20  — binary feasible flag + headroom
  tax_efficiency         0.15  — tax_saving as % of outflow
  risk_adjusted          0.10  — risk_level (low=1.0, medium=0.6, high=0.3)

Output per strategy:
  {original_strategy_fields..., score, rank, recommendation_tag}

recommendation_tag values:
  "BEST_OVERALL"   — highest composite score
  "LOWEST_COST"    — minimises total rupee outflow
  "LOWEST_RISK"    — lowest risk_level
  "FASTEST"        — shortest timeline_months
  "TAX_OPTIMAL"    — highest tax_saving
  (blank)          — other strategies

Triggers thinking_gate when top-2 scores differ by < 0.08 (near-tie).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

WEIGHTS = {
    "total_cost_efficiency": 0.30,
    "cash_flow_impact":      0.25,
    "feasibility":           0.20,
    "tax_efficiency":        0.15,
    "risk_adjusted":         0.10,
}

RISK_SCORES = {"low": 1.0, "medium": 0.6, "high": 0.3}
NEAR_TIE_THRESHOLD = 0.08


def _norm(values: list[float], invert: bool = False) -> list[float]:
    """Min-max normalise. invert=True means lower raw = higher score."""
    if not values:
        return []
    mn, mx = min(values), max(values)
    if mx == mn:
        return [0.5] * len(values)
    normed = [(v - mn) / (mx - mn) for v in values]
    return [1.0 - n for n in normed] if invert else normed


def _score_strategies(
    strategies: list[dict],
    surplus: float,
) -> list[dict]:
    """Compute per-dimension scores and composite for each strategy."""
    if not strategies:
        return []

    n = len(strategies)

    # Raw dimension values
    total_costs    = [s.get("total_cost", 0) or 0           for s in strategies]
    monthly_flows  = [s.get("monthly_outflow", 0) or 0      for s in strategies]
    tax_savings    = [s.get("tax_saving", 0) or 0           for s in strategies]
    timelines      = [s.get("timeline_months", 999) or 999  for s in strategies]

    # Normalised scores
    cost_scores    = _norm(total_costs,   invert=True)   # lower cost = higher score
    flow_scores    = _norm(monthly_flows, invert=True)   # lower outflow = higher score
    timeline_norms = _norm(timelines,     invert=True)   # faster = higher score (not in composite, used for tag)

    # Feasibility score: 1.0 if feasible + EMI headroom, 0.3 if infeasible
    feasibility_scores = []
    for s in strategies:
        if not s.get("feasible", False):
            feasibility_scores.append(0.3)
        else:
            outflow = s.get("monthly_outflow", 0) or 0
            headroom = max(0, 1.0 - (outflow / surplus)) if surplus > 0 else 0.5
            feasibility_scores.append(min(1.0, 0.7 + headroom * 0.3))

    # Tax efficiency: tax_saving / monthly_outflow (capped at 1.0)
    tax_scores = []
    for s in strategies:
        outflow = s.get("monthly_outflow", 1) or 1
        annual_tax = s.get("tax_saving", 0) or 0
        tax_scores.append(min(1.0, (annual_tax / 12) / outflow))
    tax_scores = _norm(tax_scores)  # relative ranking

    # Risk
    risk_scores = [RISK_SCORES.get(s.get("risk_level", "medium"), 0.5) for s in strategies]

    scored = []
    for i, s in enumerate(strategies):
        composite = (
            WEIGHTS["total_cost_efficiency"] * cost_scores[i] +
            WEIGHTS["cash_flow_impact"]      * flow_scores[i] +
            WEIGHTS["feasibility"]           * feasibility_scores[i] +
            WEIGHTS["tax_efficiency"]        * tax_scores[i] +
            WEIGHTS["risk_adjusted"]         * risk_scores[i]
        )
        scored.append({
            **s,
            "_scores": {
                "total_cost_efficiency": round(cost_scores[i], 3),
                "cash_flow_impact":      round(flow_scores[i], 3),
                "feasibility":           round(feasibility_scores[i], 3),
                "tax_efficiency":        round(tax_scores[i], 3),
                "risk_adjusted":         round(risk_scores[i], 3),
            },
            "composite_score": round(composite, 4),
        })

    # Tag special strategies
    scored_sorted = sorted(scored, key=lambda x: -x["composite_score"])

    best_overall_idx  = scored.index(scored_sorted[0])
    lowest_cost_idx   = total_costs.index(min(total_costs))
    lowest_risk_idx   = risk_scores.index(max(risk_scores))
    fastest_idx       = timelines.index(min(timelines))
    tax_optimal_idx   = tax_savings.index(max(tax_savings)) if max(tax_savings) > 0 else None

    for i, s in enumerate(scored):
        tags = []
        if i == best_overall_idx:
            tags.append("BEST_OVERALL")
        if i == lowest_cost_idx and i != best_overall_idx:
            tags.append("LOWEST_COST")
        if i == lowest_risk_idx and i != best_overall_idx:
            tags.append("LOWEST_RISK")
        if i == fastest_idx and i != best_overall_idx:
            tags.append("FASTEST")
        if tax_optimal_idx is not None and i == tax_optimal_idx and i != best_overall_idx:
            tags.append("TAX_OPTIMAL")
        s["recommendation_tag"] = " | ".join(tags)

    return scored


def rank_strategies(
    strategies: list[dict],
    user_profile: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Rank strategies and produce final output for TORA.

    Returns:
        {
          ranked:         list[dict] sorted by composite_score DESC,
          best:           top strategy dict,
          near_tie:       bool (triggers thinking_gate),
          recommendation: str summary for prompt injection,
        }
    """
    if not strategies:
        return {
            "ranked": [],
            "best": None,
            "near_tie": False,
            "recommendation": "No strategies available.",
        }

    profile = user_profile or {}
    surplus = float(
        profile.get("monthly_surplus") or
        profile.get("surplus") or
        profile.get("monthly_income", 0) * 0.20
    ) or 1.0
    scored  = _score_strategies(strategies, surplus)
    ranked  = sorted(scored, key=lambda x: -x["composite_score"])

    # Assign rank
    for i, s in enumerate(ranked):
        s["rank"] = i + 1

    best = ranked[0]
    near_tie = (
        len(ranked) >= 2 and
        abs(ranked[0]["composite_score"] - ranked[1]["composite_score"]) < NEAR_TIE_THRESHOLD
    )

    # Build recommendation text for prompt injection
    lines = [f"## Strategy Recommendation ({len(ranked)} options evaluated)\n"]
    for s in ranked[:3]:   # top 3 in prompt
        tag  = f" [{s['recommendation_tag']}]" if s.get("recommendation_tag") else ""
        feas = "✓" if s.get("feasible") else "✗ (may strain budget)"
        lines.append(
            f"**{s['rank']}. {s['name']}**{tag} — Score: {s['composite_score']:.2f} {feas}\n"
            f"   {s.get('description','')}\n"
            f"   Monthly: ₹{s.get('monthly_outflow',0):,} | "
            f"Total cost: ₹{s.get('total_cost',0):,} | "
            f"Interest: ₹{s.get('interest_paid',0):,} | "
            f"Tax saving: ₹{s.get('tax_saving',0):,}/yr | "
            f"Risk: {s.get('risk_level','?')}"
        )
        for note in (s.get("notes") or [])[:2]:
            lines.append(f"   • {note}")
        lines.append("")

    if near_tie:
        lines.append(
            f"⚠ Options 1 and 2 are very close (score diff {abs(ranked[0]['composite_score']-ranked[1]['composite_score']):.3f}). "
            "Recommend deeper analysis before deciding."
        )

    recommendation = "\n".join(lines)

    logger.info(
        "strategy_ranker: %d strategies, best=%r score=%.3f near_tie=%s",
        len(ranked), best.get("name"), best["composite_score"], near_tie,
    )


    recommendation = "\n".join(lines)

    logger.info(
        "strategy_ranker: %d strategies, best=%r score=%.3f near_tie=%s",
        len(ranked), best.get("name"), best["composite_score"], near_tie,
    )

    return {
        "ranked":         ranked,
        "best":           best,
        "near_tie":       near_tie,
        "recommendation": recommendation,
    }
