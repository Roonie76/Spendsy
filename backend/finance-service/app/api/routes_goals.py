"""
routes_goals.py – Finance Service Goal Management
CRUD endpoints for user Saving Goals (Phase 6).
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import UserContext, get_current_user
from app.models import FinanceGoal
from app.schemas import GoalOut, GoalPayload, GoalUpdatePayload
from app.utils.error_codes import ErrorCode
from app.utils.response import error_response, success_response

router = APIRouter(prefix="/goals", tags=["goals"])
logger = logging.getLogger("finance.goals")


def _goal_to_dict(g: FinanceGoal) -> dict:
    """Serialize a FinanceGoal to a clean dict with computed progress fields."""
    target = float(g.target_amount or 0)
    current = float(g.current_amount or 0)
    progress_pct = round((current / target * 100), 1) if target > 0 else 0.0
    remaining = max(0.0, target - current)

    # Rough projection: if target_date is set, calculate months remaining
    projected_monthly = None
    if g.target_date and not g.is_completed and g.target_date > date.today():
        months_remaining = (
            (g.target_date.year - date.today().year) * 12
            + (g.target_date.month - date.today().month)
        )
        if months_remaining > 0:
            projected_monthly = round(remaining / months_remaining, 2)

    return {
        "id": g.id,
        "title": g.title,
        "description": g.description,
        "target_amount": str(g.target_amount),
        "current_amount": str(g.current_amount),
        "target_date": g.target_date.isoformat() if g.target_date else None,
        "category": g.category,
        "is_completed": g.is_completed,
        "progress_percent": progress_pct,
        "remaining_amount": str(round(remaining, 2)),
        "projected_monthly_saving": str(projected_monthly) if projected_monthly else None,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
    }


# ─── GET /goals ────────────────────────────────────────────────────────────────

@router.get("")
def list_goals(
    request: Request,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all goals for the authenticated user, sorted by most recent."""
    goals = (
        db.query(FinanceGoal)
        .filter(FinanceGoal.user_id == user.id)
        .order_by(FinanceGoal.created_at.desc())
        .all()
    )
    return success_response(request, [_goal_to_dict(g) for g in goals], message="Goals loaded")


# ─── POST /goals ───────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_goal(
    request: Request,
    payload: GoalPayload,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new saving goal."""
    data = payload.model_dump()
    goal = FinanceGoal(
        user_id=user.id,
        title=data["title"].strip(),
        description=(data.get("description") or "").strip() or None,
        target_amount=data["target_amount"],
        current_amount=data.get("current_amount", Decimal("0")),
        target_date=data.get("target_date"),
        category=data.get("category", "savings"),
    )
    db.add(goal)
    try:
        db.commit()
        db.refresh(goal)
    except SQLAlchemyError:
        db.rollback()
        raise
    return success_response(
        request,
        _goal_to_dict(goal),
        message="Goal created successfully",
        http_status=status.HTTP_201_CREATED,
    )


# ─── PATCH /goals/{id} ─────────────────────────────────────────────────────────

@router.patch("/{goal_id}")
@router.put("/{goal_id}")
def update_goal(
    request: Request,
    goal_id: int,
    payload: GoalUpdatePayload,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partially update a goal: amount saved, title, completion flag, etc."""
    goal = db.query(FinanceGoal).filter(
        FinanceGoal.id == goal_id, FinanceGoal.user_id == user.id
    ).first()
    if goal is None:
        return error_response(request, "Goal not found", code=ErrorCode.NOT_FOUND, http_status=404)

    data = payload.model_dump(exclude_unset=True)
    if "title" in data and data["title"]:
        goal.title = data["title"].strip()
    if "description" in data:
        goal.description = (data["description"] or "").strip() or None
    if "target_amount" in data and data["target_amount"] is not None:
        goal.target_amount = data["target_amount"]
    if "current_amount" in data and data["current_amount"] is not None:
        goal.current_amount = data["current_amount"]
    if "target_date" in data:
        goal.target_date = data["target_date"]
    if "category" in data and data["category"]:
        goal.category = str(data["category"])
    if "is_completed" in data and data["is_completed"] is not None:
        goal.is_completed = data["is_completed"]

    # Auto-complete if current >= target
    if float(goal.current_amount) >= float(goal.target_amount):
        goal.is_completed = True

    goal.updated_at = datetime.utcnow()
    try:
        db.commit()
        db.refresh(goal)
    except SQLAlchemyError:
        db.rollback()
        raise

    return success_response(request, _goal_to_dict(goal), message="Goal updated")


# ─── DELETE /goals/{id} ────────────────────────────────────────────────────────

@router.delete("/{goal_id}")
def delete_goal(
    request: Request,
    goal_id: int,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a goal permanently."""
    goal = db.query(FinanceGoal).filter(
        FinanceGoal.id == goal_id, FinanceGoal.user_id == user.id
    ).first()
    if goal is None:
        return error_response(request, "Goal not found", code=ErrorCode.NOT_FOUND, http_status=404)

    db.delete(goal)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

    return success_response(request, {"id": goal_id, "deleted": True}, message="Goal deleted")
