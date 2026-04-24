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
from app.models import CreditCard, FinanceGoal, FinancePlan, FinancialInsight, ITRData, Loan, TaxProfile, ToraFeedback, Transaction, UserProfile, WealthItem
from app.utils.response import success_response
from app.services.transfer_reconciler import detect_transfer_pairs

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post("/reconcile/{user_id}")
async def trigger_reconciliation(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Trigger the transfer-pair detector for a user. Matches inter-account
    transfers (e.g. credit card bill payment from debit) so spend/income
    aggregations don't double-count them."""
    result = detect_transfer_pairs(db, user_id)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return success_response(
        request,
        {"reconciled_pairs": result.pairs_linked, "ambiguous": result.ambiguous},
        message=f"Linked {result.pairs_linked} transfer pairs",
    )


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
        Transaction.user_id == user_id, Transaction.type == "income", Transaction.is_transfer.is_(False)
    ).scalar()
    expense = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id, Transaction.type == "expense", Transaction.is_transfer.is_(False)
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
        Transaction.user_id == user_id, Transaction.type == "income", Transaction.is_transfer.is_(False)
    ).scalar()
    expense = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        Transaction.user_id == user_id, Transaction.type == "expense", Transaction.is_transfer.is_(False)
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

    # 6-month rolling trend data. Uses pre-aggregated FinancialInsight rows
    # (one per YYYY-MM period) so TORA can spot MoM shifts, seasonal patterns,
    # and category drift without dragging months of raw transactions through
    # the model's context window.
    monthly_insights = (
        db.query(FinancialInsight)
        .filter(FinancialInsight.user_id == user_id)
        .order_by(FinancialInsight.period.desc())
        .limit(6)
        .all()
    )
    monthly_trends = [
        {
            "period": ins.period,
            "total_income": float(ins.total_income or 0),
            "total_expense": float(ins.total_expense or 0),
            "net_savings": float((ins.total_income or 0) - (ins.total_expense or 0)),
            "by_category": ins.category_json or {},
            "by_merchant": ins.merchant_json or {},
        }
        for ins in reversed(monthly_insights)  # chronological order, oldest → newest
    ]
    
    payload = {
        "user_id": user_id,
        "profile": {
            "monthlyIncome": float(profile.monthly_income) if profile else 0.0,
            "monthlyBudget": float(profile.monthly_budget) if profile else 0.0,
            "dailyBudget": float(profile.daily_budget) if profile else 0.0,
            "is_business": bool(profile.is_business) if profile else False,
            "risk_tolerance": getattr(profile, "risk_tolerance", None) if profile else None,
            "dependents": int(getattr(profile, "dependents", 0) or 0) if profile else 0,
            "life_stage": getattr(profile, "life_stage", None) if profile else None,
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
                "outstanding_balance": float(getattr(c, "outstanding_balance", 0) or 0),
                "last_statement_balance": float(getattr(c, "last_statement_balance", 0) or 0),
                "payment_due_date": (
                    c.payment_due_date.isoformat()
                    if getattr(c, "payment_due_date", None)
                    else None
                ),
                "utilization_pct": (
                    round(float(c.outstanding_balance or 0) / float(c.credit_limit) * 100, 1)
                    if getattr(c, "outstanding_balance", None) is not None and float(c.credit_limit or 0) > 0
                    else None
                ),
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
                "reconciliation_flags": tx.reconciliation_flags or [],
                "created_at": tx.created_at.isoformat() if tx.created_at else None,
            }
            for tx in recent_transactions
        ],
        "monthly_trends": monthly_trends,
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


# ─── TORA Feedback (thumbs up/down) ────────────────────────────────────────

class _ToraFeedbackPayload(_BaseModel):
    """Client → ai-service → here. Any field except `rating` may be omitted."""
    rating: str  # 'up' | 'down'
    message_id: _Optional[int] = None
    client_message_id: _Optional[str] = None
    reason: _Optional[str] = None
    comment: _Optional[str] = None
    prompt: _Optional[str] = None
    response_preview: _Optional[str] = None


@router.post("/tora-feedback/{user_id}")
def save_tora_feedback(
    request: Request,
    user_id: int,
    payload: _ToraFeedbackPayload,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Persist a single thumbs up/down event on a TORA response.

    Rows are append-only. To 'change' a rating, POST a new row with the
    same `client_message_id`; the aggregation query reads the latest row.
    """
    rating = (payload.rating or "").strip().lower()
    if rating not in ("up", "down"):
        record_audit(db, request, action="internal_tora_feedback_invalid", resource_type="tora_feedback", resource_id=str(user_id), status_code=400, user=None)
        return success_response(request, {"ok": False, "error": "rating must be 'up' or 'down'"}, message="Invalid rating")

    row = ToraFeedback(
        user_id=user_id,
        message_id=payload.message_id,
        client_message_id=(payload.client_message_id or None),
        rating=rating,
        reason=(payload.reason or None),
        comment=((payload.comment or "")[:500] or None),
        prompt=((payload.prompt or "")[:500] or None),
        response_preview=((payload.response_preview or "")[:500] or None),
    )
    db.add(row)
    try:
        db.commit()
        db.refresh(row)
    except Exception:
        db.rollback()
        record_audit(db, request, action="internal_tora_feedback_error", resource_type="tora_feedback", resource_id=str(user_id), status_code=500, user=None)
        return success_response(request, {"ok": False}, message="Feedback save failed")
    record_audit(db, request, action="internal_tora_feedback_saved", resource_type="tora_feedback", resource_id=str(row.id), status_code=200, user=None)
    return success_response(request, {"ok": True, "id": row.id, "rating": rating}, message="Feedback saved")


@router.get("/tora-feedback/aggregate")
def aggregate_tora_feedback(
    request: Request,
    days: int = 7,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Roll up TORA ratings for the last `days` days.

    Returns totals, up/down split, and a per-day breakdown so you can
    plot a trend. Intentionally does NOT group by user — this is an
    operator-facing quality metric, not a user-facing dashboard.
    """
    from datetime import timedelta as _td
    cutoff = datetime.utcnow() - _td(days=max(1, min(days, 90)))

    rows = db.query(
        ToraFeedback.rating,
        func.date(ToraFeedback.created_at).label("day"),
        func.count(ToraFeedback.id).label("n"),
    ).filter(ToraFeedback.created_at >= cutoff).group_by("rating", "day").all()

    by_day: dict[str, dict[str, int]] = {}
    totals = {"up": 0, "down": 0}
    for rating, day, n in rows:
        d_key = str(day)
        by_day.setdefault(d_key, {"up": 0, "down": 0})
        by_day[d_key][rating] = int(n)
        totals[rating] = totals.get(rating, 0) + int(n)

    total_events = totals["up"] + totals["down"]
    up_rate = (totals["up"] / total_events) if total_events else None

    return success_response(
        request,
        {
            "window_days": days,
            "totals": totals,
            "up_rate": round(up_rate, 3) if up_rate is not None else None,
            "by_day": sorted(
                [{"date": d, "up": v["up"], "down": v["down"]} for d, v in by_day.items()],
                key=lambda r: r["date"],
            ),
        },
        message="Feedback aggregate",
    )


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


# ─── TORA Tax Profile Management ───────────────────────────────────────────────

class _TaxProfileUpdatePayload(_BaseModel):
    updates: dict = {}
    reason: str = "Updated via TORA AI"
    source: str = "tora_ai"


# ─── Scheduler ops — run a job on demand (dev / seeding / manual refresh) ────

@router.post("/scheduler/run/{job_id}")
def run_scheduled_job(
    request: Request,
    job_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Manually fire a scheduled job. Allowed ids:
        net_worth_snapshot, proactive_insights
    """
    from app.services.scheduler import run_job_now
    allowed = {"net_worth_snapshot", "proactive_insights"}
    if job_id not in allowed:
        return success_response(request, {"ok": False, "reason": f"Unknown job '{job_id}'. Allowed: {sorted(allowed)}"})

    # Try scheduler.run_job_now first; if scheduler isn't running (tests,
    # bare-metal ad-hoc invocations), fall back to directly importing and
    # invoking the job function.
    ok = run_job_now(job_id)
    if not ok:
        if job_id == "net_worth_snapshot":
            from app.services.jobs.net_worth_snapshot import run_daily_net_worth_snapshot as fn
        else:
            from app.services.jobs.proactive_insights import run_nightly_insights as fn
        fn()
        ok = True

    record_audit(db, request, action="scheduler_run_job", resource_type="scheduler", resource_id=job_id, status_code=200, user=None)
    return success_response(request, {"ok": ok, "job_id": job_id}, message="Job invoked")


# ─── TAX ENGINE (internal) — TORA-facing regime comparison ────────────────────
#
# The TORA `compare_tax_regimes` tool expects an internal endpoint it can
# call without user auth. Public /tax/compute exists but requires auth.

from app.services.tax_engine import (  # noqa: E402
    build_tax_input_from_itr_data,
    compare_regimes,
    compute_tax,
)
from dataclasses import asdict as _asdict  # noqa: E402


def _load_tax_input_for_user(user_id: int, db: Session, fy: str | None = None):
    """Assemble a TaxInput from the user's stored ITRData + TaxProfile."""
    itr = db.query(ITRData).filter(ITRData.user_id == user_id).first()
    tax_profile = db.query(TaxProfile).filter(TaxProfile.user_id == user_id).first()

    tax_input = build_tax_input_from_itr_data(
        itr.income_data if itr else {},
        itr.deductions_data if itr else {},
        itr.filing_details if itr else {},
        fy=fy or "FY25-26",
    )

    if tax_profile:
        tax_input.age = int(tax_profile.age or 30)
        tax_input.is_presumptive = bool(tax_profile.is_presumptive)
        tax_input.is_metro = bool(tax_profile.is_metro)
        tax_input.parents_are_senior = bool(tax_profile.parents_are_senior)
        tax_input.is_nri = bool(tax_profile.is_nri)
        tax_input.has_foreign_assets = bool(tax_profile.foreign_assets)
        # Fold top-level tax profile amounts into deductions for old-regime calc.
        tax_input.section_80d = max(
            tax_input.section_80d, float(tax_profile.health_insurance_self or 0)
        )
        tax_input.section_80d_parents = max(
            tax_input.section_80d_parents,
            float(tax_profile.health_insurance_parents or 0),
        )
        tax_input.nps_80ccd = max(tax_input.nps_80ccd, float(tax_profile.nps_contribution or 0))
        tax_input.home_loan_interest = max(
            tax_input.home_loan_interest, float(tax_profile.home_loan_interest or 0)
        )
        tax_input.section_80e = max(
            tax_input.section_80e, float(tax_profile.education_loan_interest or 0)
        )
        # HRA bootstrap from annual_rent (rough — user still needs to supply salary breakup for exact HRA exemption).
        tax_input.hra = max(tax_input.hra, float(tax_profile.annual_rent or 0))

    return tax_input


@router.get("/tax-engine/compare-regimes/{user_id}")
def internal_tax_compare_regimes(
    request: Request,
    user_id: int,
    fy: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Compare Old vs New regime for a user using stored ITR + tax profile.

    Used by the TORA agent's compare_tax_regimes tool. No user-auth required;
    gated by the internal API key.
    """
    tax_input = _load_tax_input_for_user(user_id, db, fy=fy)
    result = compare_regimes(tax_input)
    payload = {
        "user_id": user_id,
        "fy": tax_input.fy,
        "recommended_regime": result.recommended_regime,
        "savings": round(result.savings, 2),
        "breakeven_deductions": round(result.breakeven_deductions, 2),
        "old_regime_tax_liability": round(result.old_regime.total_tax, 2),
        "new_regime_tax_liability": round(result.new_regime.total_tax, 2),
        "new_regime_standard_deduction": 75_000 if tax_input.fy == "FY25-26" else 75_000,
        "old_regime": _asdict(result.old_regime),
        "new_regime": _asdict(result.new_regime),
        "old_regime_deductions": {
            "section_80c": tax_input.section_80c,
            "section_80d": tax_input.section_80d,
            "section_80d_parents": tax_input.section_80d_parents,
            "nps_80ccd": tax_input.nps_80ccd,
            "home_loan_interest": tax_input.home_loan_interest,
            "hra": tax_input.hra,
        },
        "itr_form": result.itr_form,
        "audit_errors": result.audit_errors,
        "audit_warnings": result.audit_warnings,
        "advance_tax_schedule": result.advance_tax_schedule,
        "recommendations": result.recommendations,
        "explanation": (
            f"The {result.recommended_regime} regime saves you "
            f"₹{result.savings:,.0f} under your current profile."
            if result.savings > 0
            else "Both regimes produce a similar outcome for your current profile."
        ),
    }
    record_audit(db, request, action="internal_tax_compare", resource_type="tax_regime", resource_id=str(user_id), status_code=200, user=None)
    return success_response(request, payload, message="Tax regime comparison")


@router.post("/tax-engine/simulate/{user_id}")
def internal_tax_simulate(
    request: Request,
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Run a what-if tax simulation by overlaying `profile_snapshot` fields.

    Expected payload:
        {
          "profile_snapshot": { "<any TaxInput field>": <value>, ... },
          "regime": "old" | "new"
        }
    """
    fy = payload.get("fy") or "FY25-26"
    regime = payload.get("regime", "new")
    overrides = payload.get("profile_snapshot") or {}

    base = _load_tax_input_for_user(user_id, db, fy=fy)
    # Apply numeric overrides onto the typed TaxInput — only for known fields.
    for key, value in overrides.items():
        if hasattr(base, key):
            try:
                current = getattr(base, key)
                if isinstance(current, (int, float)):
                    setattr(base, key, float(value or 0))
                elif isinstance(current, bool):
                    setattr(base, key, bool(value))
                elif isinstance(current, str):
                    setattr(base, key, str(value))
            except (TypeError, ValueError):
                continue

    breakdown = compute_tax(base, regime=regime)
    return success_response(
        request,
        {
            "tax_liability": round(breakdown.total_tax, 2),
            "taxable_income": round(breakdown.taxable_income, 2),
            "regime": regime,
            "fy": base.fy,
            "affected_deductions": list(overrides.keys()),
            "steps": [
                "Simulation overlay applied to a copy of your profile — no data was saved.",
                "Confirm the change in your tax profile to make it stick.",
            ],
            "breakdown": _asdict(breakdown),
        },
        message="Tax simulation completed",
    )


@router.get("/tax-profile/get/{user_id}")
def get_tax_profile_internal(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """Fetch user's tax profile for TORA AI (internal use only)."""
    tax_profile = db.query(TaxProfile).filter(TaxProfile.user_id == user_id).first()
    
    if not tax_profile:
        tax_profile = TaxProfile(user_id=user_id)
        db.add(tax_profile)
        try:
            db.commit()
            db.refresh(tax_profile)
        except Exception:
            db.rollback()
            raise
    
    data = {
        "id": tax_profile.id,
        "user_id": tax_profile.user_id,
        "is_business": bool(tax_profile.is_business),
        "annual_rent": float(tax_profile.annual_rent),
        "annual_epf": float(tax_profile.annual_epf),
        "nps_contribution": float(tax_profile.nps_contribution),
        "health_insurance_self": float(tax_profile.health_insurance_self),
        "health_insurance_parents": float(tax_profile.health_insurance_parents),
        "home_loan_interest": float(tax_profile.home_loan_interest),
        "education_loan_interest": float(tax_profile.education_loan_interest),
        "parents_are_senior": bool(tax_profile.parents_are_senior),
        "age": int(tax_profile.age),
        "is_metro": bool(tax_profile.is_metro),
        "is_presumptive": bool(tax_profile.is_presumptive),
        "is_nri": bool(tax_profile.is_nri),
        "foreign_assets": bool(tax_profile.foreign_assets),
        "updated_at": tax_profile.updated_at.isoformat() if tax_profile.updated_at else None,
    }
    
    record_audit(db, request, action="internal_get_tax_profile", resource_type="tax_profile", resource_id=str(user_id), status_code=200, user=None)
    return success_response(request, data)


@router.post("/tax-profile/update/{user_id}")
def update_tax_profile_internal(
    request: Request,
    user_id: int,
    payload: _TaxProfileUpdatePayload,
    db: Session = Depends(get_db),
    _: None = Depends(verify_internal_api_key),
):
    """
    Update tax profile with changes proposed by TORA AI.
    Implements the "Confirmation Shield" - only whitelisted fields are updated.
    """
    tax_profile = db.query(TaxProfile).filter(TaxProfile.user_id == user_id).first()
    
    if not tax_profile:
        tax_profile = TaxProfile(user_id=user_id)
        db.add(tax_profile)
        try:
            db.commit()
            db.refresh(tax_profile)
        except Exception:
            db.rollback()
            raise
    
    # Whitelist of fields TORA can update
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
    
    updates = payload.updates or {}
    applied_updates = {}
    
    for field, value in updates.items():
        if field not in UPDATABLE_FIELDS:
            continue
            
        # Type validation
        if field in ["is_business", "parents_are_senior", "is_metro", "is_presumptive", "is_nri", "foreign_assets"]:
            setattr(tax_profile, field, bool(value))
            applied_updates[field] = bool(value)
        elif field == "age":
            setattr(tax_profile, field, int(value))
            applied_updates[field] = int(value)
        else:
            # Numeric fields (deductions, credits)
            setattr(tax_profile, field, float(value))
            applied_updates[field] = float(value)
    
    if applied_updates:
        try:
            db.commit()
            db.refresh(tax_profile)
        except Exception:
            db.rollback()
            raise
    
    record_audit(
        db,
        request,
        action="internal_update_tax_profile",
        resource_type="tax_profile",
        resource_id=str(user_id),
        status_code=200,
        metadata={"reason": payload.reason, "source": payload.source, "fields": list(applied_updates.keys())},
        user=None
    )
    
    return success_response(
        request,
        {
            "id": tax_profile.id,
            "user_id": tax_profile.user_id,
            "applied_updates": applied_updates
        },
        message="Tax profile updated"
    )
