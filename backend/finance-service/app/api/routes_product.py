from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Any
from decimal import Decimal

from app.core.database import get_db
from app.core.security import get_current_user, UserContext
from app.schemas import DashboardOverview, FinancialHealthOut, FinancialInsightOut, SmartRecommendationOut, UserAlertOut
from app.models import FinancialHealth, FinancialInsight, SmartRecommendation, UserAlert, UserProfile, Transaction
from app.services.product_engines import HealthEngine, InsightEngine, ToraEngine
from app.core.product_tiers import TierEnforcer
from sqlalchemy import func

router = APIRouter(tags=["product"])

@router.get("/dashboard", response_model=DashboardOverview)
async def get_dashboard(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get high-level financial overview for the user."""
    user_id = user.id
    
    # Ensure health score exists
    health = db.query(FinancialHealth).filter(FinancialHealth.user_id == user_id).first()
    if not health:
        health = HealthEngine.compute_score(db, user_id)
        
    # Get latest monthly insight
    latest_period = datetime.utcnow().strftime("%Y-%m")
    insight = db.query(FinancialInsight).filter(
        FinancialInsight.user_id == user_id,
        FinancialInsight.period == latest_period
    ).first()
    if not insight:
        insight = InsightEngine.generate_monthly_insight(db, user_id, latest_period)
        
    # Recommendation count
    rec_count = db.query(SmartRecommendation).filter(
        SmartRecommendation.user_id == user_id,
        SmartRecommendation.is_dismissed == False
    ).count()
    
    # Unread alerts
    alert_count = db.query(UserAlert).filter(
        UserAlert.user_id == user_id,
        UserAlert.is_read == False
    ).count()
    
    # Top 3 categories
    top_cats = []
    if insight and insight.category_json:
        sorted_cats = sorted(insight.category_json.items(), key=lambda x: x[1], reverse=True)
        top_cats = [{"category": k, "amount": v} for k, v in sorted_cats[:3]]
        
    return DashboardOverview(
        health_score=health.score,
        monthly_income=insight.total_income,
        monthly_expense=insight.total_expense,
        savings_rate=float(health.savings_rate),
        top_categories=top_cats,
        recommendation_count=rec_count,
        unread_alerts=alert_count
    )

@router.get("/health", response_model=FinancialHealthOut)
async def get_financial_health(
    refresh: bool = False,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
    _tier: str = Depends(TierEnforcer.require_pro)
):
    """Detailed financial health score and metrics (PRO only)."""
    if refresh:
        return HealthEngine.compute_score(db, user.id)
        
    health = db.query(FinancialHealth).filter(FinancialHealth.user_id == user.id).first()
    if not health:
        health = HealthEngine.compute_score(db, user.id)
    return health

@router.get("/recommendations", response_model=List[SmartRecommendationOut])
async def get_recommendations(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
    _tier: str = Depends(TierEnforcer.require_pro)
):
    """Tora Smart Engine recommendations (PRO only)."""
    # Proactively refresh on request for now
    ToraEngine.refresh_recommendations(db, user.id)
    
    return db.query(SmartRecommendation).filter(
        SmartRecommendation.user_id == user.id,
        SmartRecommendation.is_dismissed == False
    ).order_by(SmartRecommendation.created_at.desc()).all()

@router.get("/alerts", response_model=List[UserAlertOut])
async def get_alerts(
    unread_only: bool = True,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """User-facing financial alerts."""
    query = db.query(UserAlert).filter(UserAlert.user_id == user.id)
    if unread_only:
        query = query.filter(UserAlert.is_read == False)
    return query.order_by(UserAlert.created_at.desc()).all()

@router.post("/alerts/{alert_id}/read")
async def mark_alert_as_read(
    alert_id: int,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a specific alert as read."""
    alert = db.query(UserAlert).filter(UserAlert.id == alert_id, UserAlert.user_id == user.id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    db.commit()
    return {"status": "success"}

from datetime import datetime
