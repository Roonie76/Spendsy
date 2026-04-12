from __future__ import annotations

import logging
from decimal import Decimal
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Transaction, FinancialHealth, FinancialInsight, SmartRecommendation, UserAlert, UserProfile, Loan
from app.schemas import TransactionCategory

logger = logging.getLogger(__name__)

class HealthEngine:
    """
    Computes Financial Health Score (FHS) based on savings, debt, and stability.
    """
    @staticmethod
    def compute_score(db: Session, user_id: int) -> FinancialHealth:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        income = Decimal(str(profile.monthly_income)) if profile and profile.monthly_income else Decimal("0.0")
        
        # Get last 30 days of transactions
        thirty_days_ago = datetime.utcnow().date() # Simplified
        txns = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= thirty_days_ago
        ).all()
        
        expenses = sum(t.amount for t in txns if t.type == "expense")
        savings = max(Decimal("0.0"), income - expenses)
        
        # 1. Savings Rate (40%)
        savings_rate = float(savings / income) if income > 0 else 0.0
        
        # 2. Liability Factor (30%)
        loans = db.query(Loan).filter(Loan.user_id == user_id).all()
        total_emi = sum(l.emi_amount for l in loans)
        debt_to_income = float(total_emi / income) if income > 0 else 0.0
        liability_score = max(0.0, 1.0 - debt_to_income)
        
        # 3. Stability Factor (30%)
        discretionary = sum(t.amount for t in txns if t.category in ["shopping", "entertainment", "other"])
        stability_index = float(1.0 - float(discretionary / expenses)) if expenses > 0 else 1.0
        
        # Final Score calculation
        final_score_raw = (savings_rate * 40.0) + (liability_score * 30.0) + (stability_index * 30.0)
        final_score = int(min(100, max(0, final_score_raw)))
        
        explanation = f"Your health score is {final_score}. "
        if savings_rate < 0.2:
            explanation += "Try to increase your savings rate above 20%. "
        if debt_to_income > 0.4:
            explanation += "Your debt-to-income ratio is high. "
            
        health = db.query(FinancialHealth).filter(FinancialHealth.user_id == user_id).first()
        if not health:
            health = FinancialHealth(user_id=user_id)
            db.add(health)
            
        health.score = final_score
        health.savings_rate = Decimal(str(round(savings_rate, 4)))
        health.stability_index = Decimal(str(round(stability_index, 4)))
        health.debt_to_income = Decimal(str(round(debt_to_income, 4)))
        health.explanation = explanation
        
        db.commit()
        return health


class InsightEngine:
    """
    Aggregates transactions into monthly snapshots for the dashboard.
    """
    @staticmethod
    def generate_monthly_insight(db: Session, user_id: int, period: str) -> FinancialInsight:
        # period format: YYYY-MM
        year, month = map(int, period.split("-"))
        
        txns = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            func.extract('year', Transaction.date) == year,
            func.extract('month', Transaction.date) == month
        ).all()
        
        total_income = sum(t.amount for t in txns if t.type == "income")
        total_expense = sum(t.amount for t in txns if t.type == "expense")
        
        cat_map = {}
        merchant_map = {}
        
        for t in txns:
            if t.type == "expense":
                cat_map[t.category] = float(cat_map.get(t.category, 0.0)) + float(t.amount)
                # Simple merchant detection from title
                merchant = t.title.split()[0] if t.title else "Unknown"
                merchant_map[merchant] = float(merchant_map.get(merchant, 0.0)) + float(t.amount)
                
        insight = db.query(FinancialInsight).filter(
            FinancialInsight.user_id == user_id,
            FinancialInsight.period == period
        ).first()
        
        if not insight:
            insight = FinancialInsight(user_id=user_id, period=period)
            db.add(insight)
            
        insight.total_income = total_income
        insight.total_expense = total_expense
        insight.category_json = cat_map
        insight.merchant_json = merchant_map
        
        db.commit()
        return insight


class ToraEngine:
    """
    Generates personalized recommendations (Tora Smart Engine).
    """
    @staticmethod
    def refresh_recommendations(db: Session, user_id: int):
        # Clear old recommendations for user
        db.query(SmartRecommendation).filter(
            SmartRecommendation.user_id == user_id,
            SmartRecommendation.is_dismissed == False
        ).delete()
        
        health = db.query(FinancialHealth).filter(FinancialHealth.user_id == user_id).first()
        if not health:
            return
            
        # 1. Savings Tip
        if health.savings_rate < Decimal("0.1"):
            db.add(SmartRecommendation(
                user_id=user_id,
                type="savings",
                priority="high",
                message="Your savings rate is below 10%. Consider setting up an automated transfer to your savings account."
            ))
            
        # 2. Debt Tip
        loans = db.query(Loan).filter(Loan.user_id == user_id, Loan.interest_rate > 15).all()
        if loans:
            db.add(SmartRecommendation(
                user_id=user_id,
                type="debt",
                priority="critical",
                message=f"You have {len(loans)} high-interest loans (>15%). Consider prioritizing these for early closure."
            ))
            
        # 3. Overspending (Dynamic Category Check)
        # Logic: Find top spending categories
        insight = db.query(FinancialInsight).filter(FinancialInsight.user_id == user_id).order_by(FinancialInsight.period.desc()).first()
        if insight and insight.category_json:
            # Sort categories by spending
            sorted_cats = sorted(insight.category_json.items(), key=lambda x: x[1], reverse=True)
            top_cat, top_amt = sorted_cats[0]
            if top_cat in ["shopping", "entertainment", "food"]:
                db.add(SmartRecommendation(
                    user_id=user_id,
                    type="overspending",
                    priority="medium",
                    message=f"You spent {top_amt} on {top_cat} this month. Reducing this could boost your savings by 5%."
                ))
                
        db.commit()


class AlertManager:
    """
    Scans for anomalies and risk events.
    """
    @staticmethod
    def check_for_alerts(db: Session, user_id: int, new_transaction: Transaction):
        # 1. Unusual Spike Check
        # Compare current txn with avg for same category
        avg_amt = db.query(func.avg(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.category == new_transaction.category,
            Transaction.type == new_transaction.type
        ).scalar()
        
        if avg_amt and new_transaction.amount > Decimal(str(avg_amt)) * 3:
            db.add(UserAlert(
                user_id=user_id,
                alert_type="spike",
                severity="warning",
                title="Unusual Spending Detected",
                description=f"Transaction of {new_transaction.amount} at {new_transaction.title} is 3x higher than your average for {new_transaction.category}."
            ))
            
        # 2. Duplicate Detection (Simple)
        existing = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.amount == new_transaction.amount,
            Transaction.title == new_transaction.title,
            Transaction.date == new_transaction.date,
            Transaction.id != new_transaction.id
        ).first()
        
        if existing:
             db.add(UserAlert(
                user_id=user_id,
                alert_type="duplicate",
                severity="info",
                title="Potential Duplicate Charge",
                description=f"Two identical charges of {new_transaction.amount} found at {new_transaction.title} on {new_transaction.date}."
            ))
             
        db.commit()
