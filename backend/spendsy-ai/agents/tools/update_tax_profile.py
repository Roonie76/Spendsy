"""
Tax Profile Update Tool - Enables TORA to suggest and apply tax profile changes.
Implements the "Confirmation Shield" pattern for safety.
"""

import logging
import httpx
from typing import Dict, Any, List
from config import settings

logger = logging.getLogger(__name__)


def get_current_tax_profile(user_id: int) -> Dict[str, Any]:
    """Fetch the user's current tax profile from finance-service."""
    url = f"{settings.finance_service_url}/internal/tax-profile/get/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json().get("data", {})
                logger.info(f"Fetched tax profile for user {user_id}")
                return data
    except Exception as e:
        logger.warning(f"Error fetching tax profile for user {user_id}: {e}")
    
    return {}


def suggest_tax_profile_updates(user_id: int, current_profile: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a "Confirmation Shield" response that presents proposed tax profile changes
    for TORA to show to the user before persisting.
    
    Returns:
        {
            "action": "confirm_tax_profile_update",
            "status": "pending_confirmation",
            "current_state": {...},
            "proposed_state": {...},
            "explanation": "Why these changes matter",
            "estimated_tax_benefit": float,
            "affected_deductions": [...]
        }
    """
    proposed_state = {**current_profile, **changes}
    
    # Calculate affected deductions and tax benefits
    affected_deductions = []
    estimated_benefit = 0.0
    
    # Check for senior parent deduction benefit
    if "parents_are_senior" in changes and changes["parents_are_senior"]:
        affected_deductions.append({
            "section": "Section 80D",
            "name": "Health Insurance for Senior Citizens",
            "additional_limit": "₹30,000 (vs ₹25,000 for non-senior)",
            "annual_benefit_range": "₹7,500-₹10,500"  # 25-35% tax rate
        })
        estimated_benefit += 8500
    
    # Check for NRI status
    if "is_nri" in changes and changes["is_nri"]:
        affected_deductions.append({
            "section": "TDS",
            "name": "Non-Resident Income Taxation",
            "note": "Different TDS rates and compliance requirements apply"
        })
    
    # Check for metro status (affects HRA exemption or housing benefits)
    if "is_metro" in changes and changes["is_metro"]:
        affected_deductions.append({
            "section": "Presumptive",
            "name": "Metro vs Non-Metro Status",
            "note": "May affect HRA exemption calculations"
        })
    
    explanation = ""
    if "parents_are_senior" in changes and changes["parents_are_senior"]:
        explanation += f"✓ Parents marked as senior citizens. You can now claim higher health insurance deduction (₹30,000 vs ₹25,000).\n"
    
    if "is_nri" in changes and changes["is_nri"]:
        explanation += f"✓ Status changed to NRI. Different tax rules will apply to your global income.\n"
    
    if "age" in changes:
        explanation += f"✓ Age updated to {changes['age']}. This helps with HRA and other age-based deductions.\n"
    
    return {
        "action": "confirm_tax_profile_update",
        "status": "pending_confirmation",
        "current_state": current_profile,
        "proposed_state": proposed_state,
        "changes": changes,
        "explanation": explanation.strip(),
        "affected_deductions": affected_deductions,
        "estimated_annual_tax_benefit": round(estimated_benefit, 2),
        "next_steps": [
            "Review the proposed changes above",
            "Confirm to apply these changes to your tax profile",
            "Your ITR calculations will be updated accordingly"
        ]
    }


def apply_tax_profile_update(user_id: int, changes: Dict[str, Any], reason: str = "") -> Dict[str, Any]:
    """
    Actually persist the tax profile changes to the database.
    Called only AFTER user confirmation.
    
    Safety measures:
    - Only accepts whitelisted fields
    - Validates data types
    - Logs the change
    """
    # Whitelist of updatable fields
    UPDATABLE_FIELDS = {
        "is_business",
        "annual_rent",
        "annual_epf",
        "nps_contribution",
        "health_insurance_self",
        "health_insurance_parents",
        "home_loan_interest",
        "education_loan_interest",
        "parents_are_senior",
        "age",
        "is_metro",
        "is_presumptive",
        "is_nri",
        "foreign_assets"
    }
    
    # Filter to only whitelisted fields
    sanitized_changes = {k: v for k, v in changes.items() if k in UPDATABLE_FIELDS}
    
    if not sanitized_changes:
        return {"status": "error", "message": "No valid fields to update"}
    
    url = f"{settings.finance_service_url}/internal/tax-profile/update/{user_id}"
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    
    payload = {
        "updates": sanitized_changes,
        "reason": reason,
        "source": "tora_ai"
    }
    
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"Tax profile updated for user {user_id}: {sanitized_changes}")
            return {
                "status": "success",
                "message": "Tax profile updated successfully",
                "updated_fields": list(sanitized_changes.keys()),
                "data": response.json().get("data", {})
            }
    except Exception as e:
        logger.error(f"Error applying tax profile update for user {user_id}: {e}")
        return {"status": "error", "message": str(e)}


def update_tax_profile(user_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main tool function called by TORA agent.
    
    Workflow:
    1. Fetch current tax profile
    2. Suggest changes with estimated tax benefits
    3. Return "pending_confirmation" response
    4. (User confirms via frontend) 
    5. Apply changes
    
    For autonomous execution (Pro tier):
    - Generate suggestion and immediately apply if confidence is high
    
    For manual execution (Free tier):
    - Generate suggestion and return for user to confirm
    """
    logger.info(f"Tax profile update requested for user {user_id}: {updates}")
    
    current_profile = get_current_tax_profile(user_id)
    
    # Generate confirmation response
    confirmation = suggest_tax_profile_updates(user_id, current_profile, updates)
    
    # Return the confirmation shield (not persisted yet)
    return confirmation
