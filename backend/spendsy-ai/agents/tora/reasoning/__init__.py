"""
Reasoning layer — Phase 3 + Phase 5.

Goal decomposer -> financial reasoner -> strategy ranker pipeline.
Phase 5 adds reasoning techniques (first_principles, second_order, etc.)
"""
from .goal_decomposer import decompose_goal, GoalStruct, GoalType
from .financial_reasoner import compute_strategies
from .strategy_ranker import rank_strategies
from .techniques import TECHNIQUES, TECHNIQUE_MAP, tag_techniques, build_technique_block
from .calc_verifier import verify_strategy_numbers, build_verifier_note

__all__ = [
    "decompose_goal", "GoalStruct", "GoalType",
    "compute_strategies",
    "rank_strategies",
    "TECHNIQUES", "TECHNIQUE_MAP",
    "tag_techniques", "build_technique_block",
    "verify_strategy_numbers", "build_verifier_note",
]
