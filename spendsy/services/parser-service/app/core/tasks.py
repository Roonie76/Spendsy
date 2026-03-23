import asyncio
import uuid
import time
import logging
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from pydantic import BaseModel

from app.core.pipeline import DocumentParserPipeline
from app.core.schemas import ParserResponse
from app.core.quotas import quota_manager, UserTier

logger = logging.getLogger(__name__)

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class AsyncTask(BaseModel):
    task_id: str
    user_id: str
    status: TaskStatus
    created_at: float
    updated_at: float
    result: Optional[ParserResponse] = None
    error: Optional[str] = None
    filename: str
    priority_score: float = 0.0

class AsyncTaskManager:
    """
    Advanced task manager using a priority queue for fairness and SLA enforcement.
    Implements Wait-Time Aging to prevent starvation of lower-tier tasks.
    """
    _instance = None
    _tasks: Dict[str, AsyncTask] = {}
    _queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
    _worker_task: Optional[asyncio.Task] = None
    
    # Aging factor in seconds. Larger = Newer Pro tasks win for longer.
    # 600s (10m) means a Free task waits max 10m before beating a new Pro task.
    AGING_FACTOR = 600.0 

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AsyncTaskManager, cls).__new__(cls)
        return cls._instance

    def start_worker(self):
        """Initialize the background worker if not already running."""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("Priority AsyncTaskManager worker started with Aging support")

    async def submit_task(self, content: bytes, filename: str, content_type: str, user_id: str = "anonymous") -> str:
        """Submit a new parsing job with priority scoring and quota check."""
        
        # 1. Enforcement: Check user HARD quotas
        if not quota_manager.can_submit_task(user_id):
            logger.warning(f"Submission rejected for user={user_id} - concurrency limit.")
            raise Exception(f"User {user_id} has reached their concurrency limit.")

        task_id = str(uuid.uuid4())
        now = time.time()
        
        # 2. Priority Calculation with Aging
        tier = quota_manager.get_user_tier(user_id)
        # Tier weights: Enterprise=0, Pro=1.0, Free=2.0 
        tier_weight = {
            UserTier.ENTERPRISE: 0.0, 
            UserTier.PRO:        1.0, 
            UserTier.FREE:       2.0
        }.get(tier, 2.0)
        
        # File size penalty (1MB adds 0.1 to weight, max 1.0)
        size_penalty = min((len(content) / (1024 * 1024)) * 0.1, 1.0)
        
        # Soft limit penalty (adds 0.5 to weight if user is over soft limit)
        soft_penalty = 0.5 if quota_manager.is_over_soft_limit(user_id) else 0.0
        
        # Total Base Weight
        base_weight = tier_weight + size_penalty + soft_penalty
        
        # FINAL SCORE = BaseWeight + (CreatedAt / AgingFactor)
        # As absolute time (now) increases, newer tasks get higher scores (lower priority).
        # This allows an older Free task (smaller CreatedAt) to eventually beat a newer Pro task.
        priority_score = float(base_weight) + (now / self.AGING_FACTOR)
        
        task = AsyncTask(
            task_id=task_id,
            user_id=user_id,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            filename=filename,
            priority_score=priority_score
        )
        self._tasks[task_id] = task
        
        # Track active concurrency
        quota_manager.increment_usage(user_id)
        
        # Queue item: (priority, timestamp, payload)
        # Timestamp remains as secondary tie-breaker
        await self._queue.put((priority_score, now, (task_id, content, filename, content_type)))
        
        self.start_worker()
        logger.info(f"Task {task_id} queued (tier={tier}, score={priority_score:.4f})")
        return task_id

    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        return self._tasks.get(task_id)

    async def _worker_loop(self):
        """Continuous loop processing jobs from the priority queue."""
        pipeline = DocumentParserPipeline()
        from app.core.observability import sla_tracker
        
        while True:
            score, _, payload = await self._queue.get()
            task_id, content, filename, content_type = payload
            
            task = self._tasks.get(task_id)
            if not task:
                self._queue.task_done()
                continue

            try:
                task.status = TaskStatus.RUNNING
                task.updated_at = time.time()
                
                tier = quota_manager.get_user_tier(task.user_id)
                start_proc = time.time()
                
                logger.debug(f"Worker processing task_id={task_id} score={score:.4f}")
                
                # Run pipeline with tier for SLA tracking
                result = await pipeline.run(content, filename=filename, content_type=content_type, tier=tier.value)
                
                # SLA Recording (Cross-check with pipeline-level tracking)
                duration = time.time() - start_proc
                sla_tracker.record_execution(duration, tier=tier.value)
                
                task.status = TaskStatus.COMPLETED
                task.result = result
                
            except Exception as e:
                logger.error(f"Background task {task_id} failed: {str(e)}")
                task.status = TaskStatus.FAILED
                task.error = str(e)
            
            finally:
                task.updated_at = time.time()
                quota_manager.decrement_usage(task.user_id)
                self._queue.task_done()
                logger.debug(f"Worker finished task_id={task_id}")

# Global instance
task_manager = AsyncTaskManager()
