from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException

from app.core.pipeline import DocumentParserPipeline
from app.core.internal_auth import verify_internal_api_key
from app.utils.files import validate_file_security, sanitize_filename
from app.core.tasks import task_manager
from app.core.registry import ParserRegistry

router = APIRouter(tags=["parser"])

pipeline = DocumentParserPipeline()


@router.post("/parse")
async def parse_statement(
    file: UploadFile = File(...),
    async_mode: bool = Query(False, alias="async"),
    user_id: str = Query("anonymous"),
    _: None = Depends(verify_internal_api_key),
):
    """
    Parse a bank statement. 
    If async=true, returns a task_id immediately and processes in background.
    """
    from app.core.safety import safety_manager
    from app.core.quotas import quota_manager
    from app.core.cache import result_cache
    from app.core.observability import cost_guard

    if not safety_manager.is_system_enabled():
        raise HTTPException(status_code=503, detail="System processing is currently disabled via kill switch.")

    # Internal defense-in-depth: Validate file even from internal services
    validate_file_security(file)
    filename = sanitize_filename(file.filename or "statement.pdf")

    content = await file.read()
    
    # ── Stage 0: Cache Check ──────────────────────────────────────────
    cached_result = result_cache.get(content)
    if cached_result:
        return cached_result.model_dump(mode="json")

    # ── Stage 1: Quota check ──────────────────────────────────────────
    # UserQuotaManager now supports soft limits (accepted with penalty in AsyncTaskManager)
    # But hard limits still immediate rejection.
    if not quota_manager.can_submit_task(user_id):
        raise HTTPException(status_code=429, detail="User HARD concurrency limit reached.")

    # ── Stage 1b: Task Submission ─────────────────────────────────────
    if async_mode:
        task_id = await task_manager.submit_task(content, filename, file.content_type, user_id=user_id)
        return {"task_id": task_id, "status": "accepted"}

    # Track usage for sync mode too
    tier = quota_manager.get_user_tier(user_id)
    quota_manager.increment_usage(user_id)
    try:
        # Run pipeline with tier for SLA monitoring
        result = await pipeline.run(content, filename=filename, content_type=file.content_type, user_id=user_id, tier=tier.value)
        
        # ── Stage 2: Cache Update ─────────────────────────────────────
        result_cache.set(content, result)
        
        # ── Stage 3: Cost Guard Update ────────────────────────────────
        total_cost = sum([result.meta.get("parser_cost", 0.0)]) # Basic total for now
        cost_guard.record_cost(user_id, total_cost)
        
        return result.model_dump(mode="json")
    finally:
        quota_manager.decrement_usage(user_id)


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Poll for the status and result of a background parsing task."""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.model_dump(mode="json")


@router.get("/registry/status")
async def get_registry_status(_: None = Depends(verify_internal_api_key)):
    """Check the active versions of all registered parsers."""
    return {
        "active_versions": ParserRegistry._active_versions,
        "available_versions": {
            name: list(versions.keys()) 
            for name, versions in ParserRegistry._parsers.items()
        }
    }


@router.post("/registry/rollback/{parser_type}")
async def rollback_parser_version(
    parser_type: str, 
    _: None = Depends(verify_internal_api_key)
):
    """Rollback a specific parser to its previous version."""
    ParserRegistry.rollback_version(parser_type)
    return {
        "message": f"Rollback performed for {parser_type}",
        "new_version": ParserRegistry._active_versions.get(parser_type)
    }
