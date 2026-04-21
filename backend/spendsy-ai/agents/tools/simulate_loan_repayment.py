"""
Loan Repayment Simulation Tool - Enables TORA to run multi-loan scenarios
and help users optimize debt payoff strategies.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


def calculate_loan_amortization(
    principal: float,
    annual_rate: float,
    monthly_payment: float,
    months_remaining: int
) -> List[Dict[str, Any]]:
    """
    Calculate detailed amortization schedule for a loan.
    
    Returns list of months with breakdown of:
    - Principal payment
    - Interest payment
    - Remaining balance
    - Monthly surplus/deficit
    """
    schedule = []
    balance = Decimal(str(principal))
    monthly_rate = Decimal(str(annual_rate)) / Decimal("1200")  # Convert annual % to monthly
    payment = Decimal(str(monthly_payment))
    
    for month in range(1, min(months_remaining + 1, 61)):  # Limit to 60 months for readability
        interest_payment = balance * monthly_rate
        principal_payment = payment - interest_payment
        balance = balance - principal_payment
        
        schedule.append({
            "month": month,
            "principal_payment": float(principal_payment),
            "interest_payment": float(interest_payment),
            "remaining_balance": float(max(balance, 0)),
            "total_payment": float(payment)
        })
        
        if balance <= 0:
            break
    
    return schedule


def simulate_extra_payment_impact(
    principal: float,
    annual_rate: float,
    monthly_emi: float,
    extra_monthly_payment: float
) -> Dict[str, Any]:
    """
    Calculate impact of making extra monthly payments toward a loan.
    Shows months saved and total interest saved.
    """
    # Standard scenario (EMI only)
    standard_months = 0
    standard_interest = 0
    balance = Decimal(str(principal))
    monthly_rate = Decimal(str(annual_rate)) / Decimal("1200")
    emi = Decimal(str(monthly_emi))
    
    while balance > 0 and standard_months < 360:
        interest = balance * monthly_rate
        principal_paid = emi - interest
        balance -= principal_paid
        standard_interest += float(interest)
        standard_months += 1
    
    # Accelerated scenario (EMI + extra payment)
    accelerated_months = 0
    accelerated_interest = 0
    balance = Decimal(str(principal))
    accelerated_payment = emi + Decimal(str(extra_monthly_payment))
    
    while balance > 0 and accelerated_months < 360:
        interest = balance * monthly_rate
        principal_paid = accelerated_payment - interest
        balance -= principal_paid
        accelerated_interest += float(interest)
        accelerated_months += 1
    
    months_saved = standard_months - accelerated_months
    interest_saved = standard_interest - accelerated_interest
    
    return {
        "scenario": "Extra Monthly Payment Impact",
        "extra_payment": float(extra_monthly_payment),
        "standard_completion": {
            "months": standard_months,
            "total_interest_paid": round(standard_interest, 2)
        },
        "accelerated_completion": {
            "months": accelerated_months,  
            "total_interest_paid": round(accelerated_interest, 2)
        },
        "impact": {
            "months_saved": months_saved,
            "interest_saved": round(interest_saved, 2),
            "interest_saved_percentage": round((interest_saved / standard_interest) * 100, 2) if standard_interest > 0 else 0,
            "recommendation": "highly_recommended" if interest_saved > (extra_monthly_payment * 12 * 2) else "recommended"
        }
    }


def simulate_multi_loan_payoff_strategy(
    loans: List[Dict[str, Any]],
    available_monthly_surplus: float,
    strategy: str = "debt_snowball"
) -> Dict[str, Any]:
    """
    Simulate different multi-loan payoff strategies.
    
    Strategies:
    - debt_snowball: Pay smallest loan first (psychological wins)
    - debt_avalanche: Pay highest interest rate first (financial optimization)
    - proportional: Distribute surplus proportionally across all loans
    
    Returns timeline showing which loans get paid off first and overall payoff date.
    """
    
    # Sort loans based on strategy
    if strategy == "debt_snowball":
        sorted_loans = sorted(loans, key=lambda x: x.get("remaining_balance", 0))
    elif strategy == "debt_avalanche":
        sorted_loans = sorted(loans, key=lambda x: x.get("interest_rate", 0), reverse=True)
    else:  # proportional
        sorted_loans = loans
    
    months_to_payoff = 0
    total_interest_paid = 0
    payoff_sequence = []
    
    for loan in sorted_loans:
        principal = float(loan.get("remaining_balance", 0))
        rate = float(loan.get("interest_rate", 10)) / 100
        emi = float(loan.get("emi_amount", principal * 0.05))
        
        monthly_rate = rate / 12
        extra_payment = available_monthly_surplus / len(sorted_loans)
        total_payment = emi + extra_payment
        
        balance = Decimal(str(principal))
        months = 0
        interest = 0
        
        while balance > 0 and months < 360:
            interest_payment = balance * Decimal(str(monthly_rate))
            principal_payment = Decimal(str(total_payment)) - interest_payment
            balance -= principal_payment
            interest += float(interest_payment)
            months += 1
        
        payoff_sequence.append({
            "loan_type": loan.get("loan_type", "unknown"),
            "original_balance": principal,
            "months_to_payoff": months,
            "total_interest_paid": round(interest, 2)
        })
        
        months_to_payoff += months
        total_interest_paid += interest
    
    return {
        "scenario": "Multi-Loan Payoff Strategy",
        "strategy": strategy,
        "monthly_surplus": available_monthly_surplus,
        "payoff_sequence": payoff_sequence,
        "total_months_all_loans": months_to_payoff,
        "total_interest_paid_all_loans": round(total_interest_paid, 2),
        "completion_date": (date.today() + timedelta(days=months_to_payoff * 30)).isoformat(),
        "pro_tier_analysis": {
            "priority": "Pay off high-interest loans first to minimize total interest",
            "alternative_strategies": ["debt_snowball", "debt_avalanche", "proportional"]
        }
    }


def simulate_loan_consolidation(
    loans: List[Dict[str, Any]],
    weighted_interest_rate: float,
    new_tenure_months: int
) -> Dict[str, Any]:
    """
    Pro tier feature: Simulate impact of consolidating multiple loans into one.
    
    Shows:
    - New combined EMI
    - Total interest over new tenure
    - Comparison with current trajectory
    - Break-even analysis
    """
    
    total_principal = sum(float(l.get("remaining_balance", 0)) for l in loans)
    current_total_emi = sum(float(l.get("emi_amount", 0)) for l in loans)
    
    # Calculate new EMI for consolidated loan
    principal = Decimal(str(total_principal))
    monthly_rate = Decimal(str(weighted_interest_rate)) / Decimal("1200")
    num_months = Decimal(str(new_tenure_months))
    
    # EMI formula: P * [r(1+r)^n] / [(1+r)^n - 1]
    compound = (1 + monthly_rate) ** num_months
    new_emi_decimal = principal * (monthly_rate * compound) / (compound - 1)
    new_emi = float(new_emi_decimal)
    
    # Calculate total interest for consolidated loan
    total_payments = new_emi * new_tenure_months
    total_interest_consolidated = total_payments - total_principal
    
    return {
        "scenario": "Loan Consolidation Analysis",
        "current_state": {
            "total_principal": total_principal,
            "total_emi": round(current_total_emi, 2),
            "number_of_loans": len(loans)
        },
        "consolidated_state": {
            "total_principal": total_principal,
            "new_emi": round(new_emi, 2),
            "tenure_months": new_tenure_months,
            "weighted_interest_rate": weighted_interest_rate,
            "total_interest_payable": round(total_interest_consolidated, 2)
        },
        "financial_impact": {
            "monthly_emi_change": round(new_emi - current_total_emi, 2),
            "monthly_emi_change_percentage": round(((new_emi - current_total_emi) / current_total_emi) * 100, 2),
            "simplified_payments": True,
            "recommendation": "Recommended" if new_emi < current_total_emi else "Review consolidation charges"
        },
        "pro_tier_feature": True
    }


def simulate_loan_repayment(user_id: int, simulation_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main tool function for loan repayment simulations.
    
    Available simulations:
    - extra_payment: Impact of extra monthly payments
    - multi_loan_strategy: Compare payoff strategies
    - consolidation: Consolidate multiple loans
    
    Arguments:
        simulation_type: Type of simulation to run
        params: Dict with simulation parameters
    """
    
    logger.info(f"Loan simulation for user {user_id}: {simulation_type}")
    
    if simulation_type == "extra_payment":
        result = simulate_extra_payment_impact(
            principal=params.get("principal", 0),
            annual_rate=params.get("annual_rate", 10),
            monthly_emi=params.get("monthly_emi", 0),
            extra_monthly_payment=params.get("extra_payment", 0)
        )
    
    elif simulation_type == "multi_loan_strategy":
        result = simulate_multi_loan_payoff_strategy(
            loans=params.get("loans", []),
            available_monthly_surplus=params.get("monthly_surplus", 0),
            strategy=params.get("strategy", "debt_avalanche")
        )
    
    elif simulation_type == "consolidation":
        result = simulate_loan_consolidation(
            loans=params.get("loans", []),
            weighted_interest_rate=params.get("weighted_rate", 9.5),
            new_tenure_months=params.get("tenure_months", 60)
        )
    
    else:
        return {"status": "error", "message": f"Unknown simulation type: {simulation_type}"}
    
    result["action"] = "loan_repayment_simulation"
    result["user_id"] = user_id
    result["generated_at"] = datetime.utcnow().isoformat() + "Z"
    
    return result
