import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Simple Circuit Breaker to prevent cascading failures for external API calls (LLM, Cloud).
    """
    def __init__(self, name: str, threshold: int = 3, reset_timeout: int = 60):
        self.name = name
        self.threshold = threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.is_open = False

    def can_execute(self) -> bool:
        if self.is_open:
            if time.time() - self.last_failure_time > self.reset_timeout:
                logger.info(f"CircuitBreaker {self.name} resetting to HALF-OPEN")
                return True
            return False
        return True

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.threshold:
            self.is_open = True
            logger.warning(f"CircuitBreaker {self.name} OPEN")

    def record_success(self):
        self.failure_count = 0
        self.is_open = False


from app.core.redis import get_redis

class CostTracker:
    RATES = {
        "llm_token_input_mio": 0.15,
        "llm_token_output_mio": 0.60,
        "ocr_page": 0.0015,
        "cloud_api_call": 0.01
    }

    @classmethod
    def estimate_llm_cost(cls, input_tokens: int, output_tokens: int) -> float:
        in_cost = (input_tokens / 1_000_000) * cls.RATES["llm_token_input_mio"]
        out_cost = (output_tokens / 1_000_000) * cls.RATES["llm_token_output_mio"]
        return in_cost + out_cost

    @classmethod
    def estimate_ocr_cost(cls, pages: int = 1) -> float:
        return pages * cls.RATES["ocr_page"]


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
llm_breaker = CircuitBreaker("LLM_Local")
cloud_breaker = CircuitBreaker("Cloud_Gemini")
cost_tracker = CostTracker()
sla_tracker = SLATracker()
cost_guard = UserCostGuard()
