"""In-process job scheduler for finance-service.

Runs with the FastAPI app (no separate worker container required).
Jobs live in `app.services.jobs.*` and are registered here.

Startup is wired in `app/main.py` via the lifespan handler. The scheduler
is disabled automatically in test runs (set `FINANCE_SCHEDULER_ENABLED=0`
or rely on the default pytest guard) so unit tests don't fire real jobs.

Job inventory (see docstrings in each job module for specifics):
    • net_worth_snapshot — daily 00:15 IST. Walks every user, writes one
      `NetWorthSnapshot` row.
    • proactive_insights — nightly 02:00 IST. Scans last 30 days of
      transactions per user, writes `UserAlert` rows for MoM shifts,
      unusual merchants, and large single transactions.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("finance.scheduler")

# Module-level singleton. `None` until `start_scheduler()` runs, back to
# None after `stop_scheduler()`. This shape makes it trivial to skip the
# scheduler entirely in tests and to detect double-start in dev reloads.
_scheduler: AsyncIOScheduler | None = None


def _is_enabled() -> bool:
    """Respect explicit opt-out for tests and constrained local runs."""
    raw = os.getenv("FINANCE_SCHEDULER_ENABLED", "1")
    return raw.lower() not in ("0", "false", "no", "off")


def _register_jobs(scheduler: AsyncIOScheduler) -> None:
    """Wire every job. Isolated so tests can stub individual jobs."""
    # Import inside the function so a bad import in one job doesn't prevent
    # the scheduler from starting at all.
    from app.services.jobs.net_worth_snapshot import run_daily_net_worth_snapshot
    from app.services.jobs.proactive_insights import run_nightly_insights

    scheduler.add_job(
        _safely(run_daily_net_worth_snapshot, "net_worth_snapshot"),
        CronTrigger(hour=0, minute=15),  # 00:15 server time
        id="net_worth_snapshot",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        _safely(run_nightly_insights, "proactive_insights"),
        CronTrigger(hour=2, minute=0),
        id="proactive_insights",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def _safely(fn: Callable[[], None], name: str) -> Callable[[], None]:
    """Wrap a job so a crash doesn't poison the scheduler."""
    def _wrapped() -> None:
        started = datetime.utcnow()
        logger.info("scheduler: starting job %s", name)
        try:
            fn()
        except Exception:
            logger.exception("scheduler: job %s crashed", name)
        else:
            elapsed = (datetime.utcnow() - started).total_seconds()
            logger.info("scheduler: job %s finished in %.2fs", name, elapsed)

    _wrapped.__name__ = f"safe_{name}"
    return _wrapped


def start_scheduler() -> AsyncIOScheduler | None:
    """Start the background scheduler if enabled. Idempotent."""
    global _scheduler
    if not _is_enabled():
        logger.info("scheduler disabled via FINANCE_SCHEDULER_ENABLED")
        return None
    if _scheduler is not None:
        logger.debug("scheduler: already started")
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    _register_jobs(_scheduler)
    _scheduler.start()
    job_names = [j.id for j in _scheduler.get_jobs()]
    logger.info("scheduler started with jobs: %s", job_names)
    return _scheduler


def stop_scheduler() -> None:
    """Shut the scheduler down. Idempotent."""
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
    except Exception:
        logger.exception("scheduler: shutdown failed")
    _scheduler = None


def get_scheduler() -> AsyncIOScheduler | None:
    """Primarily for tests / debug endpoints that want to trigger jobs manually."""
    return _scheduler


def run_job_now(job_id: str) -> bool:
    """Manually fire a registered job (bypasses the cron trigger).

    Returns True on success, False if the scheduler isn't running or the
    job id is unknown. Useful for the ops debug endpoint.
    """
    scheduler = _scheduler
    if scheduler is None:
        return False
    job = scheduler.get_job(job_id)
    if job is None:
        return False
    # APScheduler runs the job function inline — it's already wrapped with _safely.
    job.func()
    return True
