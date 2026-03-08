from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.internal_auth import verify_internal_api_key
from ..models import ITRData, TaxProfile, Transaction, UserProfile, WealthItem
from ..utils.response import success_response

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/finance-context/{user_id}")
def finance_context(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    tax_profile = db.query(TaxProfile).filter(TaxProfile.user_id == user_id).first()
    itr = db.query(ITRData).filter(ITRData.user_id == user_id).first()

    income = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id, Transaction.type == "income"
    ).scalar()
    expense = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id, Transaction.type == "expense"
    ).scalar()
    count = db.query(func.count(Transaction.id)).filter(Transaction.user_id == user_id).scalar()

    wealth_items = db.query(WealthItem).filter(WealthItem.user_id == user_id).all()
    wealth_assets = sum(float(item.amount) for item in wealth_items if item.type == "asset")
    wealth_liabilities = sum(float(item.amount) for item in wealth_items if item.type == "liability")

    recent_transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(8)
        .all()
    )

    payload = {
        "user_id": user_id,
        "profile": {
            "monthlyIncome": float(profile.monthly_income) if profile else 0.0,
            "monthlyBudget": float(profile.monthly_budget) if profile else 0.0,
            "dailyBudget": float(profile.daily_budget) if profile else 0.0,
            "is_business": bool(profile.is_business) if profile else False,
            "email": None,
        },
        "summary": {
            "income": float(income or 0),
            "expense": float(expense or 0),
            "balance": float((income or 0) - (expense or 0)),
            "transaction_count": int(count or 0),
        },
        "wealth": {
            "assets": float(wealth_assets),
            "liabilities": float(wealth_liabilities),
            "net_worth": float(wealth_assets - wealth_liabilities),
        },
        "tax_profile": {
            "isBusiness": bool(tax_profile.is_business) if tax_profile else False,
            "annualRent": float(tax_profile.annual_rent) if tax_profile else 0.0,
            "annualEPF": float(tax_profile.annual_epf) if tax_profile else 0.0,
            "npsContribution": float(tax_profile.nps_contribution) if tax_profile else 0.0,
            "healthInsuranceSelf": float(tax_profile.health_insurance_self) if tax_profile else 0.0,
            "healthInsuranceParents": float(tax_profile.health_insurance_parents) if tax_profile else 0.0,
            "homeLoanInterest": float(tax_profile.home_loan_interest) if tax_profile else 0.0,
            "educationLoanInterest": float(tax_profile.education_loan_interest) if tax_profile else 0.0,
        },
        "itr": {
            "income_data": itr.income_data if itr else {},
            "deductions_data": itr.deductions_data if itr else {},
            "filing_details": itr.filing_details if itr else {},
            "tax_regime": itr.tax_regime if itr else "new",
        },
        "recent_transactions": [
            {
                "id": tx.id,
                "title": tx.title,
                "amount": float(tx.amount),
                "type": tx.type,
                "category": tx.category,
                "date": tx.date.isoformat(),
                "is_recurring": tx.is_recurring,
            }
            for tx in recent_transactions
        ],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    return success_response(request, payload, message="Finance context")
