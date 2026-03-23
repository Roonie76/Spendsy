import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class TierConfig:
    def __init__(self, concurrency_limit: int, monthly_limit: int, soft_limit: int | None = None):
        self.concurrency_limit = concurrency_limit
        self.monthly_limit = monthly_limit
        self.soft_limit = soft_limit or concurrency_limit

TIER_LIMITS = {
    UserTier.FREE: TierConfig(concurrency_limit=5, monthly_limit=50, soft_limit=3),
    UserTier.PRO: TierConfig(concurrency_limit=15, monthly_limit=1000, soft_limit=10),
    UserTier.ENTERPRISE: TierConfig(concurrency_limit=50, monthly_limit=100000, soft_limit=40),
}

class UserQuotaManager:
    """
    Manages per-user concurrency and usage limits.
    Supports soft limits (accept with penalty) and hard limits (reject).
    """
    _instance = None
    _active_concurrent: Dict[str, int] = {} # user_id -> count
    _user_tiers: Dict[str, UserTier] = {}    # user_id -> tier

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UserQuotaManager, cls).__new__(cls)
        return cls._instance

    def set_user_tier(self, user_id: str, tier: UserTier):
        self._user_tiers[user_id] = tier

    def get_user_tier(self, user_id: str) -> UserTier:
        return self._user_tiers.get(user_id, UserTier.FREE)

    def can_submit_task(self, user_id: str) -> bool:
        """Check if user has reached their HARD concurrency limit."""
        tier = self.get_user_tier(user_id)
        limit = TIER_LIMITS[tier].concurrency_limit
        current = self._active_concurrent.get(user_id, 0)
        
        if current >= limit:
            logger.warning(f"User {user_id} ({tier}) reached HARD concurrency limit: {current}/{limit}")
            return False
        return True

    def is_over_soft_limit(self, user_id: str) -> bool:
        """Check if user has exceeded their soft limit but is under hard limit."""
        tier = self.get_user_tier(user_id)
        limit = TIER_LIMITS[tier].soft_limit
        current = self._active_concurrent.get(user_id, 0)
        return current >= limit

    def increment_usage(self, user_id: str):
        self._active_concurrent[user_id] = self._active_concurrent.get(user_id, 0) + 1
        logger.debug(f"User {user_id} concurrent tasks: {self._active_concurrent[user_id]}")

    def decrement_usage(self, user_id: str):
        if user_id in self._active_concurrent:
            self._active_concurrent[user_id] = max(0, self._active_concurrent[user_id] - 1)
            logger.debug(f"User {user_id} concurrent tasks: {self._active_concurrent[user_id]}")

# Global instance
quota_manager = UserQuotaManager()
