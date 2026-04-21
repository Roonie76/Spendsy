"""
Tax Regime Comparison & Simulation Tool - Enables TORA to run "What-if" scenarios
for Old vs New tax regimes with personalized analysis.
"""

import logging
import httpx
from typing import Dict, Any
from config import settings

logger = logging.getLogger(__name__)


def call_tax_engine_compare(user_id: int) -> Dict[str, Any]:
    """
    Call the tax-service compare_regimes endpoint to get Old vs New regime comparison.
    Returns detailed liability breakdown for both regimes.
    """
    url = f"{settings.finance_service_url}/internal/tax-engine/compare-regimes/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json().get("data", {})
                logger.info(f"Tax regime comparison fetched for user {user_id}")
                return data
    except Exception as e:
        logger.warning(f"Error fetching tax regime comparison: {e}")
    
    return {}


def simulate_tax_profile_change(
    user_id: int,
    current_profile: Dict[str, Any],
    proposed_changes: Dict[str, Any],
    regime: str = "new"
) -> Dict[str, Any]:
    """
    Simulate tax liability change if the user applies the proposed tax profile changes.
    
    Example: User updates parents_are_senior = True
    Simulation shows: "New 80D limit saves you ₹7,500 in taxes"
    """
    
    # Apply changes to a copy of the profile
    simulated_profile = {**current_profile, **proposed_changes}
    
    # Call tax engine with the simulated profile
    url = f"{settings.finance_service_url}/internal/tax-engine/simulate/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    payload = {
        "profile_snapshot": simulated_profile,
        "regime": regime
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                data = response.json().get("data", {})
                logger.info(f"Tax simulation completed for user {user_id}")
                return data
    except Exception as e:
        logger.warning(f"Error simulating tax profile change: {e}")
    
    return {}


def compare_tax_regimes(user_id: int) -> Dict[str, Any]:
    """
    Main tool function - Compare Old vs New tax regimes for a user.
    
    Pro tier feature: Enables detailed "What-if" analysis
    Free tier: Only regime explanation (no simulation)
    
    Returns:
        {
            "status": "success",
            "recommendation": "new" | "old",
            "reason": "New regime saves you ₹X annually",
            "old_regime": {
                "total_tax_liability": float,
                "deductions_available": {...},
                "advantages": [...]
            },
            "new_regime": {
                "total_tax_liability": float,
                "standard_deduction": float,
                "advantages": [...]
            },
            "income_bracket_impact": string,
            "filing_complexity": "Old regime is more complex"
        }
    """
    logger.info(f"Tax regime comparison initiated for user {user_id}")
    
    comparison = call_tax_engine_compare(user_id)
    
    if not comparison or "error" in comparison:
        return {
            "status": "error",
            "message": "Unable to fetch tax regime comparison. Try again later."
        }
    
    # Format the comparison for TORA's narrative
    return {
        "status": "success",
        "action": "tax_regime_comparison",
        "user_id": user_id,
        "old_regime": {
            "total_tax_liability": comparison.get("old_regime_tax_liability", 0),
            "applicable_deductions": comparison.get("old_regime_deductions", {}),
            "advantages": [
                "Can claim all available deductions",
                "Beneficial if you have high deductible expenses",
                "More complex filing with schedule requirements"
            ]
        },
        "new_regime": {
            "total_tax_liability": comparison.get("new_regime_tax_liability", 0),
            "standard_deduction": comparison.get("new_regime_standard_deduction", 50000),
            "advantages": [
                "Simpler filing process",
                "Lower tax rates",
                "No schedule attachments needed",
                "Better for salaried individuals"
            ]
        },
        "recommendation": comparison.get("recommended_regime", "new"),
        "estimated_tax_savings": round(
            abs(comparison.get("old_regime_tax_liability", 0) - comparison.get("new_regime_tax_liability", 0)),
            2
        ),
        "explanation": comparison.get("explanation", "Compare the two regimes based on your income and deductions."),
        "pro_tier_features": {
            "whatif_scenarios": "Run custom scenarios with proposed changes",
            "detailed_breakdown": "See impact of each deduction",
            "portfolio_analysis": "Get investment recommendations based on tax efficiency"
        }
    }


def simulate_tax_whatif(
    user_id: int,
    scenario_description: str,
    profile_changes: Dict[str, Any],
    regime: str = "new"
) -> Dict[str, Any]:
    """
    Pro tier feature: Simulate custom "What-if" tax scenarios.
    
    Examples:
    - "What if I contribute ₹1,50,000 to NPS?"
    - "What if my parents become senior citizens?"
    - "What if I buy home insurance?"
    
    Arguments:
        scenario_description: Natural language description of the scenario
        profile_changes: Dict of profile fields to change for simulation
        regime: Which tax regime to simulate ("old" or "new")
    
    Returns:
        {
            "scenario": "What if I contribute ₹1,50,000 to NPS?",
            "regime": "new",
            "current_tax_liability": float,
            "simulated_tax_liability": float,
            "tax_savings": float,
            "implementation_steps": [...]
        }
    """
    logger.info(f"Tax What-if simulation for user {user_id}: {scenario_description}")
    
    current_profile = call_tax_engine_compare(user_id)
    
    simulation = simulate_tax_profile_change(
        user_id,
        current_profile,
        profile_changes,
        regime
    )
    
    current_liability = current_profile.get(f"{regime}_regime_tax_liability", 0)
    simulated_liability = simulation.get("tax_liability", current_liability)
    
    return {
        "status": "success",
        "action": "tax_whatif_simulation",
        "scenario": scenario_description,
        "regime": regime,
        "current_tax_liability": float(current_liability),
        "simulated_tax_liability": float(simulated_liability),
        "tax_savings": round(float(current_liability) - float(simulated_liability), 2),
        "tax_savings_percentage": round(
            (float(current_liability) - float(simulated_liability)) / float(current_liability) * 100,
            2
        ) if current_liability > 0 else 0,
        "affected_deductions": simulation.get("affected_deductions", []),
        "implementation_steps": simulation.get("steps", []),
        "recommendation": "Recommended" if simulated_liability < current_liability else "Not recommended",
        "pro_tier_feature": True
    }
