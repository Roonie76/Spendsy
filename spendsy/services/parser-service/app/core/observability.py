import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# CostTracker removed (AI-only)


class UserCostGuard:
    """
    Enforces per-user spending limits.
    Now persists data in Redis under 'parser:user_costs' hash.
    """
    BUDGETS = {
        "free": 1.00,
        "pro": 25.00,
        "enterprise": 500.0
    }

    @classmethod
    def record_cost(cls, user_id: str, cost: float):
        try:
            get_redis().hincrbyfloat("parser:user_costs", user_id, cost)
        except Exception: pass

    @classmethod
    def is_within_budget(cls, user_id: str, tier: str = "free") -> bool:
        budget = cls.BUDGETS.get(tier, 1.00)
        try:
            current = get_redis().hget("parser:user_costs", user_id)
            return float(current or 0.0) < budget
        except Exception:
            return True


class SLATracker:
    THRESHOLDS = {
        "free": 15.0,
        "pro": 7.0,
        "enterprise": 3.0
    }

    @classmethod
    def record_execution(cls, duration: float, tier: str = "free", parser_name: Optional[str] = None):
        limit = cls.THRESHOLDS.get(tier, 15.0)
        if duration > limit:
            logger.warning(f"SLA VIOLATION: tier={tier} parser={parser_name} duration={duration:.2f}s limit={limit}s")
            if parser_name:
                try:
                    get_redis().hincrby("parser:sla_violations", parser_name, 1)
                except Exception: pass

    @classmethod
    def get_violation_count(cls, parser_name: str) -> int:
        try:
            count = get_redis().hget("parser:sla_violations", parser_name)
            return int(count or 0)
        except Exception:
            return 0


class MetricsCollector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MetricsCollector, cls).__new__(cls)
        return cls._instance

    def record_usage(self, parser_name: str, duration: float, success: bool, tx_count: int = 0, cost: float = 0.0, bank: str = "unknown"):
        try:
            r = get_redis()
            # 1. Parser Stats
            r.hincrby(f"parser:stats:{parser_name}", "calls", 1)
            r.hincrbyfloat(f"parser:stats:{parser_name}", "total_time", duration)
            r.hincrbyfloat(f"parser:stats:{parser_name}", "total_cost", cost)
            if success:
                r.hincrby(f"parser:stats:{parser_name}", "successes", 1)

            # 2. Bank Stats
            r.hincrby(f"parser:bank_stats:{bank}", "calls", 1)
            if success:
                r.hincrby(f"parser:bank_stats:{bank}", "successes", 1)

            r.hincrbyfloat("parser:globals", "total_cost", cost)
        except Exception as e:
            logger.debug(f"Metrics record failed: {e}")

    def get_stats(self) -> Dict[str, Any]:
        try:
            r = get_redis()
            # Simplified aggregate fetch - for full stats, one would scan keys
            return {
                "total_cost": float(r.hget("parser:globals", "total_cost") or 0.0)
            }
        except Exception:
            return {"total_cost": 0.0}

metrics = MetricsCollector()
# llm_breaker = CircuitBreaker("LLM_Local")
# cloud_breaker = CircuitBreaker("Cloud_Gemini")
# cost_tracker = CostTracker()
sla_tracker = SLATracker()
cost_guard = UserCostGuard()
