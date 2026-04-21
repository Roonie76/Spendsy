"""
Investment & Tax Optimization Simulation Tool - Pro tier feature
Enables TORA to recommend tax-efficient investment allocations and calculate
impact on tax liability, post-tax returns, and wealth accumulation.
"""

import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


def calculate_investment_allocation(
    annual_income: float,
    savings_rate: float,
    investment_horizon_years: int,
    risk_profile: str = "moderate"
) -> Dict[str, Any]:
    """
    Recommend tax-efficient investment allocation based on income and risk profile.
    
    Risk profiles: conservative, moderate, aggressive
    Allocations consider: Equity, Debt, Gold, Real Estate, NPS (tax-deferred)
    """
    
    annual_savings = annual_income * savings_rate
    
    # Base allocations by risk profile
    allocations = {
        "conservative": {
            "nps": 0.30,        # Tax-deferred growth, 50% withdrawal tax-free post 60
            "debt_mutual_funds": 0.25,  # Indexation benefit after 3 years
            "fixed_deposits": 0.25,     # Safe, but taxable
            "gold": 0.15,       # No TDS, long-term LTCG at 20%
            "real_estate": 0.05
        },
        "moderate": {
            "nps": 0.20,        # Tax-deferred
            "equity_mutual_funds": 0.35,  # LTCG 0% up to ₹1L, then 20%
            "debt_mutual_funds": 0.20,
            "fixed_deposits": 0.15,
            "gold": 0.05,
            "real_estate": 0.05
        },
        "aggressive": {
            "nps": 0.15,
            "equity_mutual_funds": 0.50,
            "debt_mutual_funds": 0.10,
            "fixed_deposits": 0.10,
            "gold": 0.05,
            "real_estate": 0.10
        }
    }
    
    selected = allocations.get(risk_profile, allocations["moderate"])
    
    return {
        "annual_savings": annual_savings,
        "risk_profile": risk_profile,
        "investment_horizon_years": investment_horizon_years,
        "recommended_allocation": {
            instrument: round(annual_savings * pct, 2)
            for instrument, pct in selected.items()
        },
        "allocation_percentages": selected,
        "tax_advantages": {
            "nps": "Deduction under 80C (up to ₹1.5L), tax-free growth",
            "equity_mutual_funds": "LTCG at 0% up to ₹1L per year, enhanced indexation for older funds",
            "debt_mutual_funds": "Indexation benefit reduces taxable gain",
            "fixed_deposits": "Interest taxed as income, but safe option",
            "gold": "No TDS, LTCG at 20% after 3 years",
            "real_estate": "Section 80C on principal, 24(1)(vii) on interest"
        }
    }


def calculate_tax_impact_of_investments(
    gross_income: float,
    investments: Dict[str, float],
    current_tax_liability: float
) -> Dict[str, Any]:
    """
    Calculate how different investment strategies impact tax liability.
    
    Considers:
    - Section 80C deductions (NPS, life insurance, home loan principal)
    - Section 80D (health insurance)
    - Long-term capital gains tax rates
    - Dividend income tax rates
    """
    
    deductible_80c = (
        investments.get("nps", 0) +
        investments.get("life_insurance", 0) +
        investments.get("home_loan_principal", 0)
    )
    # Cap at ₹1.5L
    deductible_80c = min(deductible_80c, 150000)
    
    # Calculate taxable income after 80C deduction
    taxable_income = gross_income - deductible_80c
    
    # Simplified tax calculation (new regime bands for FY 2025-26)
    if taxable_income <= 300000:
        tax_new_regime = 0
    elif taxable_income <= 700000:
        tax_new_regime = (taxable_income - 300000) * 0.05
    elif taxable_income <= 1000000:
        tax_new_regime = 20000 + (taxable_income - 700000) * 0.10
    elif taxable_income <= 1700000:
        tax_new_regime = 50000 + (taxable_income - 1000000) * 0.15
    else:
        tax_new_regime = 155000 + (taxable_income - 1700000) * 0.30
    
    # Add cess
    tax_new_regime_with_cess = tax_new_regime * 1.04
    
    # Old regime (roughly, with 80C deduction)
    old_regime_taxable = gross_income - deductible_80c
    if old_regime_taxable <= 250000:
        tax_old_regime = 0
    elif old_regime_taxable <= 500000:
        tax_old_regime = (old_regime_taxable - 250000) * 0.05
    elif old_regime_taxable <= 1000000:
        tax_old_regime = 12500 + (old_regime_taxable - 500000) * 0.20
    else:
        tax_old_regime = 112500 + (old_regime_taxable - 1000000) * 0.30
    
    tax_old_regime_with_cess = tax_old_regime * 1.04
    
    tax_saving = abs(tax_new_regime_with_cess - tax_old_regime_with_cess)
    
    return {
        "scenario": "Investment Impact on Tax Liability",
        "investments_made": investments,
        "total_80c_deductions": round(deductible_80c, 2),
        "taxable_income_after_deductions": round(taxable_income, 2),
        "new_regime_tax": round(tax_new_regime_with_cess, 2),
        "old_regime_tax": round(tax_old_regime_with_cess, 2),
        "tax_saving": round(tax_saving, 2),
        "recommendation": "Old Regime" if tax_old_regime_with_cess < tax_new_regime_with_cess else "New Regime",
        "investment_roi_after_tax": {
            "equity_mutual_funds_ltcg_zero_tax": "Up to ₹1L in gains, then 20%",
            "nps_immediate_deduction": f"₹{round(min(investments.get('nps', 0), 150000), 2)} saved in tax this year"
        }
    }


def simulate_sip_growth_with_tax(
    monthly_sip: float,
    years: int,
    annual_return: float,
    instrument_type: str = "equity_mutual_fund"
) -> Dict[str, Any]:
    """
    Simulate SIP growth with tax optimization.
    
    Shows post-tax returns for:
    - Equity (LTCG 0% up to ₹1L)
    - Debt (Indexation benefit)
    - Balanced funds
    """
    
    months = years * 12
    balance = 0.0
    total_invested = monthly_sip * months
    
    monthly_rate = (annual_return / 100) / 12
    
    # Calculate final value
    for month in range(1, months + 1):
        balance = balance * (1 + monthly_rate) + monthly_sip
    
    total_gain = balance - total_invested
    
    # Tax calculation based on instrument type
    if instrument_type == "equity_mutual_fund":
        # LTCG at 0% up to ₹1L, then 20%
        if total_gain <= 100000:
            tax_on_gain = 0
        else:
            tax_on_gain = (total_gain - 100000) * 0.20
        tax_regime = "LTCG - 0% up to ₹1L, 20% thereafter"
    
    elif instrument_type == "debt_mutual_fund":
        # Indexation benefit (approx 20% reduction in gain)
        indexed_gain = total_gain * 0.80
        tax_on_gain = indexed_gain * 0.30  # Taxed as income
        tax_regime = "Taxed as income with indexation benefit"
    
    elif instrument_type == "gold":
        # Gold ETF - LTCG at 20% after 3 years
        if years >= 3 and total_gain > 0:
            tax_on_gain = total_gain * 0.20
            tax_regime = "LTCG 20% (after 3 years)"
        else:
            tax_on_gain = total_gain  # STCG at income rate
            tax_regime = "STCG at income rate (before 3 years)"
    
    else:  # nps or fixed deposits
        tax_on_gain = total_gain * 0.30
        tax_regime = "Taxed as income"
    
    post_tax_balance = balance - tax_on_gain
    post_tax_return = ((post_tax_balance - total_invested) / total_invested * 100) if total_invested > 0 else 0
    
    return {
        "scenario": "SIP Growth Simulation with Tax Optimization",
        "parameters": {
            "monthly_sip": monthly_sip,
            "years": years,
            "annual_return_percent": annual_return,
            "instrument": instrument_type,
            "total_invested": round(total_invested, 2)
        },
        "pre_tax_results": {
            "final_balance": round(balance, 2),
            "total_gain": round(total_gain, 2),
            "gain_percentage": round((total_gain / total_invested) * 100, 2)
        },
        "post_tax_results": {
            "tax_regime": tax_regime,
            "tax_on_gain": round(tax_on_gain, 2),
            "final_balance_after_tax": round(post_tax_balance, 2),
            "post_tax_return_percentage": round(post_tax_return, 2)
        },
        "pro_tier_insight": {
            "optimal_window": "Book profits when you have ₹1L LTCG zero-tax window",
            "tax_loss_harvesting": "Consider offsetting STCG with STCL",
            "equity_advantage": "Equity mutual funds offer best tax efficiency long-term"
        }
    }


def simulate_tax_efficient_investment_plan(
    user_id: int,
    gross_income: float,
    savings_rate: float,
    investment_horizon_years: int,
    current_tax_liability: float,
    risk_profile: str = "moderate"
) -> Dict[str, Any]:
    """
    Comprehensive investment x tax optimization simulation (Pro tier).
    
    Combines allocation, tax impact, and SIP growth projections.
    """
    
    logger.info(f"Investment planning for user {user_id}: income={gross_income}, savings_rate={savings_rate}")
    
    # Get recommended allocation
    allocation = calculate_investment_allocation(
        gross_income,
        savings_rate,
        investment_horizon_years,
        risk_profile
    )
    
    # Calculate tax impact
    tax_impact = calculate_tax_impact_of_investments(
        gross_income,
        allocation["recommended_allocation"],
        current_tax_liability
    )
    
    # Get SIP growth for primary instrument
    annual_savings = gross_income * savings_rate
    monthly_sip = annual_savings / 12
    
    equity_sip = calculate_sip_growth_with_tax(
        monthly_sip * 0.35,  # 35% to equity
        investment_horizon_years,
        11.0,  # ~11% average stock market return
        "equity_mutual_fund"
    )
    
    debt_sip = calculate_sip_growth_with_tax(
        monthly_sip * 0.20,  # 20% to debt
        investment_horizon_years,
        7.0,  # ~7% debt return
        "debt_mutual_fund"
    )
    
    nps_sip = calculate_sip_growth_with_tax(
        monthly_sip * 0.20,  # 20% to NPS
        investment_horizon_years,
        9.0,  # ~9% NPS return
        "nps"
    )
    
    return {
        "action": "tax_efficient_investment_plan",
        "user_id": user_id,
        "allocation": allocation,
        "tax_impact": tax_impact,
        "sip_projections": {
            "equity_mutual_funds": equity_sip,
            "debt_mutual_funds": debt_sip,
            "nps": nps_sip
        },
        "summary": {
            "annual_investment": round(annual_savings, 2),
            "projected_wealth_5_years": round(
                equity_sip["post_tax_results"]["final_balance_after_tax"] +
                debt_sip["post_tax_results"]["final_balance_after_tax"] +
                nps_sip["post_tax_results"]["final_balance_after_tax"],
                2
            ),
            "tax_saving_this_year": round(tax_impact.get("tax_saving", 0), 2),
            "recommended_regime": tax_impact.get("recommendation", "New Regime")
        },
        "pro_tier_feature": True,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }
