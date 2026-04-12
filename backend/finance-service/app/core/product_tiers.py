from __future__ import annotations

import logging
from enum import Enum
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, UserContext
from app.models import UserProfile, StatementRecord

logger = logging.getLogger(__name__)

class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class TierConfig:
    # Upload limits per month
    MAX_UPLOADS = {
        UserTier.FREE: 100,
        UserTier.PRO: 50,
        UserTier.ENTERPRISE: 1000
    }
    
    # Feature availability
    HAS_ADVANCED_INSIGHTS = {
        UserTier.FREE: False,
        UserTier.PRO: True,
        UserTier.ENTERPRISE: True
    }

class TierEnforcer:
    """
    Gates access to product features based on user tier.
    """
    @staticmethod
    def get_tier(db: Session, user_id: int) -> UserTier:
        profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile or not profile.tier:
            return UserTier.FREE
        try:
            return UserTier(profile.tier.lower())
        except ValueError:
            return UserTier.FREE

    @staticmethod
    def check_upload_limit(db: Session, user_id: int):
        tier = TierEnforcer.get_tier(db, user_id)
        limit = TierConfig.MAX_UPLOADS.get(tier, 5)
        
        # Count uploads this month
        import datetime
        first_day = datetime.date.today().replace(day=1)
        count = db.query(StatementRecord).filter(
            StatementRecord.user_id == user_id,
            StatementRecord.created_at >= first_day
        ).count()
        
        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Monthly upload limit reached for {tier} tier ({limit} uploads). Please upgrade for more."
            )

    @staticmethod
    def require_pro(user: UserContext = Depends(get_current_user), db: Session = Depends(get_db)):
        tier = TierEnforcer.get_tier(db, user.id)
        if tier == UserTier.FREE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This feature requires a PRO or ENTERPRISE subscription."
            )
        return tier
