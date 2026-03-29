from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core import cryptography as security_crypto
from app.core.audit import record_audit
from app.core.database import get_db
from app.core.internal_auth import verify_internal_api_key
from app.core.security import RequireRole, UserContext, get_current_user
from app.models import CreditCard, FinanceGoal, FinancePlan, ITRData, Loan, TaxProfile, Transaction, UserProfile, WealthItem
from app.utils.response import success_response

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/transactions/{user_id}")
def list_transactions(
    request: Request,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    
    data = [
        {
            "id": tx.id,
            "title": tx.title,
            "amount": float(tx.amount),
            "type": tx.type,
            "category": tx.category,
            "date": tx.date.isoformat(),
            "is_recurring": tx.is_recurring,
        }
        for tx in transactions
    ]
    record_audit(db, request, action="internal_list_transactions", resource_type="user_transactions", resource_id=str(user_id), status_code=200, user=None)
    return success_response(request, data)


@router.get("/summary/{user_id}")
def get_summary(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    income = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id, Transaction.type == "income"
    ).scalar()
    expense = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id, Transaction.type == "expense"
    ).scalar()
    count = db.query(func.count(Transaction.id)).filter(Transaction.user_id == user_id).scalar()

    record_audit(db, request, action="internal_get_summary", resource_type="user_summary", resource_id=str(user_id), status_code=200, user=None)
    return success_response(request, {
        "income": float(income or 0),
        "expense": float(expense or 0),
        "balance": float((income or 0) - (expense or 0)),
        "transaction_count": int(count or 0),
    })


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
    credit_cards = db.query(CreditCard).filter(CreditCard.user_id == user_id).all()
    loans = db.query(Loan).filter(Loan.user_id == user_id).all()
    goals = db.query(FinanceGoal).filter(FinanceGoal.user_id == user_id).all()
    plans = db.query(FinancePlan).filter(FinancePlan.user_id == user_id).all()
    wealth_assets = sum(float(item.amount) for item in wealth_items if item.type == "asset")
    wealth_liabilities = sum(float(item.amount) for item in wealth_items if item.type == "liability")

    recent_transactions = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .limit(50)
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
        "credit_cards": [
            {
                "id": c.id,
                "name": c.bank_name,
                "credit_limit": float(c.credit_limit or 0),
            }
            for c in credit_cards
        ],
        "loans": [
            {
                "id": l.id,
                "loan_type": l.loan_type,
                "principal_amount": float(l.principal_amount or 0),
                "remaining_balance": float(l.remaining_balance or 0),
                "interest_rate": float(l.interest_rate or 0),
                "emi_amount": float(l.emi_amount or 0),
                "tenure_months": l.tenure_months,
            }
            for l in loans
        ],
        "goals": [
            {
                "id": g.id,
                "title": g.title,
                "description": g.description,
                "target_amount": float(g.target_amount),
                "current_amount": float(g.current_amount),
                "target_date": g.target_date.isoformat() if g.target_date else None,
                "category": g.category,
                "is_completed": g.is_completed,
            }
            for g in goals
        ],
        "plans": [
            {
                "id": p.id,
                "title": p.title,
                "target_amount": float(p.target_amount),
                "current_saved": float(p.current_saved),
                "deadline": p.deadline.isoformat(),
                "status": p.status,
            }
            for p in plans
        ],
        "recent_transactions": [
            {
                "id": tx.id,
                "title": (tx.raw_description or tx.title or "Untitled Transaction").strip() or "Untitled Transaction",
                "description": (tx.raw_description or tx.title or "Untitled Transaction").strip() or "Untitled Transaction",
                "raw_description": tx.raw_description,
                "amount": float(tx.amount),
                "type": tx.type,
                "category": tx.category,
                "date": tx.date.isoformat(),
                "balance": float(tx.balance) if tx.balance is not None else None,
                "source": tx.source,
                "is_recurring": tx.is_recurring,
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in recent_transactions
        ],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    record_audit(db, request, action="internal_finance_context", resource_type="user_context", resource_id=str(user_id), status_code=200, user=None)
    return success_response(request, payload, message="Finance context")


# ─── TORA Conversation History ─────────────────────────────────────────────────

from app.models import ToraConversation
from pydantic import BaseModel as _BaseModel
from typing import Optional as _Optional

class _ToraMsgPayload(_BaseModel):
    role: str
    content: str
    financial_overview: _Optional[str] = None
    current_position: _Optional[str] = None
    recommended_strategy: _Optional[str] = None
    expected_outcome: _Optional[str] = None


@router.post("/tora-conversation/{user_id}")
def save_tora_message(
    request: Request,
    user_id: int,
    payload: _ToraMsgPayload,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Persist a single TORA conversation turn (user or assistant)."""
    msg = ToraConversation(
        user_id=user_id,
        role=payload.role,
        content=security_crypto.encrypt_string(payload.content[:2000]),
        financial_overview=security_crypto.encrypt_string((payload.financial_overview or "")[:2000] or None),
        current_position=security_crypto.encrypt_string((payload.current_position or "")[:2000] or None),
        recommended_strategy=security_crypto.encrypt_string((payload.recommended_strategy or "")[:4000] or None),
        expected_outcome=security_crypto.encrypt_string((payload.expected_outcome or "")[:2000] or None),
    )
    db.add(msg)
    try:
        db.commit()
        db.refresh(msg)
    except Exception:
        db.rollback()
        record_audit(db, request, action="internal_save_tora_msg_error", resource_type="tora_conversation", resource_id=str(user_id), status_code=500, user=None)
        raise
    record_audit(db, request, action="internal_save_tora_msg", resource_type="tora_conversation", resource_id=str(user_id), status_code=200, user=None)
    return success_response(request, {"id": msg.id}, message="Message saved")


@router.get("/tora-conversation/{user_id}")
def get_tora_history(
    request: Request,
    user_id: int,
    limit: int = 10,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Fetch the N most recent TORA conversation turns for a user."""
    msgs = (
        db.query(ToraConversation)
        .filter(ToraConversation.user_id == user_id)
        .order_by(ToraConversation.created_at.desc())
        .limit(limit)
        .all()
    )
    # Reverse to chronological order for prompt injection
    msgs = list(reversed(msgs))
    data = [
        {
            "id": m.id,
            "role": m.role,
            "content": security_crypto.decrypt_string(m.content),
            "financial_overview": security_crypto.decrypt_string(m.financial_overview),
            "current_position": security_crypto.decrypt_string(m.current_position),
            "recommended_strategy": security_crypto.decrypt_string(m.recommended_strategy),
            "expected_outcome": security_crypto.decrypt_string(m.expected_outcome),
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]
    record_audit(db, request, action="internal_get_tora_history", resource_type="tora_conversation", resource_id=str(user_id), status_code=200, user=None)
    return success_response(request, data, message="Conversation history")


# ─── TORA Goal Management ──────────────────────────────────────────────────────

from app.models import FinanceGoal

class _InternalGoalPayload(_BaseModel):
    title: str
    description: _Optional[str] = None
    target_amount: float
    current_amount: float
    target_date: str
    category: str
    is_completed: bool

@router.post("/goals/{user_id}")
def internal_create_goal(
    request: Request,
    user_id: int,
    payload: _InternalGoalPayload,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Create a goal on behalf of the user (used by TORA AI)."""
    from datetime import datetime
    try:
        # TORA sends ISO strings like 2027-01-01T00:00:00Z
        parsed_date = datetime.fromisoformat(payload.target_date.replace("Z", "+00:00")).date()
    except Exception:
        from datetime import date
        parsed_date = date.today()

    goal = FinanceGoal(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        target_amount=payload.target_amount,
        current_amount=payload.current_amount,
        target_date=parsed_date,
        category=payload.category,
        is_completed=payload.is_completed,
    )
    db.add(goal)
    try:
        db.commit()
        db.refresh(goal)
    except Exception:
        db.rollback()
        record_audit(db, request, action="internal_create_goal_error", resource_type="finance_goal", resource_id=str(user_id), status_code=500, user=None)
        raise
    
    record_audit(db, request, action="internal_create_goal", resource_type="finance_goal", resource_id=str(goal.id), status_code=201, user=None)
    return success_response(request, {"id": goal.id}, message="Goal created")

@router.delete("/goals/{user_id}/{goal_id}")
def internal_delete_goal(
    request: Request,
    user_id: int,
    goal_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Delete a goal on behalf of the user (used by TORA AI)."""
    goal = db.query(FinanceGoal).filter(FinanceGoal.id == goal_id, FinanceGoal.user_id == user_id).first()
    if not goal:
        return {"status": "error", "message": "Goal not found"}
        
    try:
        db.delete(goal)
        db.commit()
    except Exception:
        db.rollback()
        record_audit(db, request, action="internal_delete_goal_error", resource_type="finance_goal", resource_id=str(goal_id), status_code=500, user=None)
        raise
        
    record_audit(db, request, action="internal_delete_goal", resource_type="finance_goal", resource_id=str(goal_id), status_code=200, user=None)
    return success_response(request, {"id": goal_id}, message="Goal deleted")


# ─── TORA Planner System ───────────────────────────────────────────────────────

class _InternalPlanPayload(_BaseModel):
    title: str
    source: str = "manual"
    loan_id: _Optional[int] = None
    target_amount: float
    current_saved: float = 0
    deadline: str
    monthly_saving: float
    daily_saving: float
    confidence_score: _Optional[float] = 1.0
    reasoning: _Optional[str] = None
    status: str = "on_track"

@router.post("/plans/create/{user_id}")
def internal_create_plan(
    request: Request,
    user_id: int,
    payload: _InternalPlanPayload,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Create a detailed finance plan (used by TORA AI or Dashboard)."""
    try:
        parsed_date = datetime.fromisoformat(payload.deadline.replace("Z", "+00:00")).date()
    except Exception:
        from datetime import date
        parsed_date = date.today()

    plan = FinancePlan(
        user_id=user_id,
        title=payload.title,
        source=payload.source,
        target_amount=payload.target_amount,
        current_saved=payload.current_saved,
        loan_id=payload.loan_id,
        deadline=parsed_date,
        monthly_saving=payload.monthly_saving,
        daily_saving=payload.daily_saving,
        confidence_score=payload.confidence_score,
        reasoning=payload.reasoning,
        status=payload.status,
    )
    db.add(plan)
    try:
        db.commit()
        db.refresh(plan)
    except Exception:
        db.rollback()
        raise
    
    record_audit(db, request, action="internal_create_plan", resource_type="finance_plan", resource_id=str(plan.id), status_code=201, user=None)
    return success_response(request, {"id": plan.id}, message="Plan created")

class _InternalPlanAdjustPayload(_BaseModel):
    title: _Optional[str] = None
    loan_id: _Optional[int] = None
    monthly_saving: _Optional[float] = None
    deadline: _Optional[str] = None
    status: _Optional[str] = None
    reasoning: _Optional[str] = None

@router.post("/plans/adjust/{user_id}/{plan_id}")
def internal_adjust_plan(
    request: Request,
    user_id: int,
    plan_id: int,
    payload: _InternalPlanAdjustPayload,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Adjust an existing finance plan."""
    plan = db.query(FinancePlan).filter(FinancePlan.id == plan_id, FinancePlan.user_id == user_id).first()
    if not plan:
        return {"status": "error", "message": "Plan not found"}

    if payload.monthly_saving is not None:
        plan.monthly_saving = payload.monthly_saving
        # Also update daily saving
        plan.daily_saving = float(payload.monthly_saving) / 30
        
    if payload.deadline:
        try:
            plan.deadline = datetime.fromisoformat(payload.deadline.replace("Z", "+00:00")).date()
        except Exception:
            pass
            
    if payload.status:
        plan.status = payload.status
        
    if payload.reasoning:
        plan.reasoning = payload.reasoning
        
    if payload.loan_id is not None:
        plan.loan_id = payload.loan_id

    if payload.title:
        plan.title = payload.title

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
        
    record_audit(db, request, action="internal_adjust_plan", resource_type="finance_plan", resource_id=str(plan_id), status_code=200, user=None)
    return success_response(request, {"id": plan.id}, message="Plan adjusted")

@router.get("/plans/list/{user_id}")
def internal_list_plans(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """List all finance plans for a user."""
    plans = db.query(FinancePlan).filter(FinancePlan.user_id == user_id).all()
    data = [
        {
            "id": p.id,
            "uid": p.uid,
            "title": p.title,
            "source": p.source,
            "loan_id": p.loan_id,
            "target_amount": float(p.target_amount),
            "current_saved": float(p.current_saved),
            "deadline": p.deadline.isoformat(),
            "monthly_saving": float(p.monthly_saving),
            "daily_saving": float(p.daily_saving),
            "confidence_score": float(p.confidence_score),
            "reasoning": p.reasoning,
            "status": p.status,
            "created_at": p.created_at.isoformat(),
        }
        for p in plans
    ]
    record_audit(db, request, action="internal_list_plans", resource_type="user_plans", resource_id=str(user_id), status_code=200, user=None)
    return success_response(request, data)
