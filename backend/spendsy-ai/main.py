from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agents.tora_agent import handle_user_question
from config import settings
from tiering import TieringConfig
import httpx
import logging
import os
from tracer import HAS_LIGHTNING, tracer, lightning_store

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI(title="Ask Tora AI Service")

# Add CORS middleware — restrict to known frontend origins
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Initialize Agent Lightning (Microsoft) for production observability and RL
if HAS_LIGHTNING:
    logger.info("Agent Lightning initialized.")
else:
    logger.warning("Agent Lightning not found. Tracing disabled. Run 'pip install agentlightning' to enable.")


class QuestionRequest(BaseModel):
    user_id: int = 1
    question: str
    model: str | None = None  # Optional; will be auto-selected based on tier if None
    tier: str | None = None   # Optional; will be auto-fetched if None


class FeedbackRequest(BaseModel):
    """Thumbs up/down from the chat UI.

    `client_message_id` is whatever the frontend generated for the chat
    bubble; we use it to dedupe repeat clicks and let users change their
    vote without creating new bubble ids.
    """
    user_id: int
    rating: str  # 'up' | 'down'
    client_message_id: str | None = None
    message_id: int | None = None
    reason: str | None = None
    comment: str | None = None
    prompt: str | None = None
    response_preview: str | None = None
    trace_id: str | None = None  # Link to Agent Lightning trace

@app.get("/")
def root():
    return {"status": "healthy", "service": "spendsy-ai"}


@app.get("/health")
async def health_check():
    """Deep health check — verifies Ollama connectivity and model availability."""
    from agents.llm_router import check_ollama_health
    ollama = check_ollama_health()
    primary = settings.model_gemma
    fallback = settings.model_llama
    models_available = ollama.get("models", [])

    status = "healthy" if ollama["ok"] else "degraded"
    details = {
        "service": "spendsy-ai",
        "ollama_url": settings.ollama_base_url,
        "ollama_connected": ollama["ok"],
        "primary_model": primary,
        "primary_loaded": primary in models_available,
        "fallback_model": fallback,
        "fallback_loaded": fallback in models_available,
    }
    if not ollama["ok"]:
        details["ollama_error"] = ollama.get("error", "unknown")
        details["fix"] = "Run 'ollama serve' on the host machine"
    elif primary not in models_available:
        status = "degraded"
        details["fix"] = f"Run 'ollama pull {primary}'"

    return {"status": status, **details}


async def fetch_user_tier(user_id: int) -> str:
    """
    Fetch user tier from finance-service internal API.
    Falls back to 'free' if unavailable.

    TODO: re-enable when tier/subscription is implemented in finance-service.
    """
    # Tier system not yet implemented — skip the finance-service call entirely.
    return "free"


@app.post("/ask-tora")
async def handle_ask_tora(request: QuestionRequest):
    if not request.question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        # If tier not provided, fetch from database
        user_tier = request.tier or await fetch_user_tier(request.user_id)
        
        # If model not provided, select based on tier
        selected_model = request.model or TieringConfig.get_model_for_tier(user_tier)
        
        logger.info(f"User {request.user_id} (tier={user_tier}) using model={selected_model}")
        
        # Route to the TORA Agent with tier and model information
        # Wrapped in Agent Lightning tracer if available
        if HAS_LIGHTNING:
            with tracer.trace(agent_id="tora", input=request.question) as span:
                answer = await handle_user_question(
                    request.user_id,
                    request.question,
                    selected_model,
                    user_tier
                )
                if "error" not in answer:
                    span.set_output(answer)
                    span.set_metadata({
                        "user_id": request.user_id,
                        "tier": user_tier,
                        "model": selected_model
                    })
                    # Attach trace_id so frontend can relay it back in /feedback
                    answer["trace_id"] = span.trace_id
        else:
            answer = await handle_user_question(
                request.user_id,
                request.question,
                selected_model,
                user_tier
            )

        if "error" in answer:
            raise HTTPException(status_code=500, detail=answer["error"])
        return {"answer": answer}
    except Exception as e:
        logger.error(f"TORA endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def submit_feedback(payload: FeedbackRequest):
    """Relay thumbs up/down to finance-service AND trigger re-evaluation.

    When rating == 'up', re-evaluates the trace with user_feedback='up'
    so high-quality real responses are stored in the reasoning hot index.
    """
    rating = (payload.rating or "").strip().lower()
    if rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating must be 'up' or 'down'")
    url = f"{settings.finance_service_url}/internal/tora-feedback/{payload.user_id}"
    body = payload.model_dump(exclude={"user_id"})
    body["rating"] = rating
    try:
        if HAS_LIGHTNING and payload.trace_id:
            feedback_reward = 1.0 if rating == "up" else 0.0
            engagement_bonus = 0.1 if payload.comment or payload.reason else 0.0
            composite_reward = (feedback_reward * 0.7) + engagement_bonus
            lightning_store.log_reward(trace_id=payload.trace_id, reward=composite_reward)
            logger.info(f"Logged composite reward {composite_reward} for trace {payload.trace_id}")

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                url,
                json=body,
                headers={"X-Internal-API-Key": settings.internal_api_key},
            )
        if response.status_code >= 500:
            raise HTTPException(status_code=502, detail="Feedback service unavailable")

        # Re-evaluate and store in reasoning hot index (fire-and-forget)
        if payload.prompt and payload.response_preview:
            import asyncio as _asyncio
            _asyncio.create_task(
                _reevaluate_and_store(
                    query=payload.prompt,
                    response_text=payload.response_preview,
                    user_feedback=rating,
                    user_id=payload.user_id,
                )
            )

        return response.json()
    except httpx.HTTPError as e:
        logger.warning(f"Feedback relay failed for user {payload.user_id}: {e}")
        raise HTTPException(status_code=502, detail="Feedback relay failed")


async def _reevaluate_and_store(
    query: str,
    response_text: str,
    user_feedback: str,
    user_id: int,
) -> None:
    """Re-score a response with real user feedback and store winners in hot index."""
    try:
        from fine_tuning.evaluator import evaluate
        from fine_tuning.reasoning_store import save as rs_save
        from agents.tora.reasoning.goal_decomposer import decompose_goal

        goal = decompose_goal(query)
        goal_type = goal.goal_type.value

        result = evaluate(
            query=query,
            response_text=response_text,
            goal_type=goal_type,
            user_feedback=user_feedback,
        )
        logger.info(
            "Re-eval feedback=%s score=%.3f winner=%s goal=%s user=%s",
            user_feedback, result.score, result.is_winner, goal_type, user_id,
        )
        if result.is_winner:
            rs_save(
                query=query,
                goal_struct=goal.raw_entities,
                response_text=response_text,
                eval_result=result,
                user_id=user_id,
            )
            logger.info("Feedback winner stored in hot index: user=%s goal=%s", user_id, goal_type)
    except Exception as exc:
        logger.warning("_reevaluate_and_store failed: %s", exc)


async def _nightly_feedback_batch() -> None:
    """
    Nightly batch: pull thumbs-up conversations from finance-service,
    re-evaluate each with user_feedback='up', store winners in hot index.
    Scheduled at 02:00 IST daily via APScheduler (wired in startup_event).
    """
    logger.info("Nightly feedback batch starting")
    try:
        from fine_tuning.collect import fetch_feedback_rows
        rows = fetch_feedback_rows(min_rating="up", limit=500)
        stored = 0
        for row in rows:
            q   = row.get("prompt", "")
            rsp = row.get("response_preview", "")
            uid = row.get("user_id", 0)
            if q and rsp:
                await _reevaluate_and_store(q, rsp, "up", uid)
                stored += 1
        logger.info("Nightly feedback batch: %d rows processed", stored)
    except Exception as exc:
        logger.warning("Nightly feedback batch failed: %s", exc)


@app.on_event("startup")
async def startup_event():
    """Wire APScheduler for nightly feedback batch at 02:00 IST."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
        scheduler.add_job(
            _nightly_feedback_batch,
            trigger="cron",
            hour=2,
            minute=0,
            id="nightly_feedback_batch",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started — nightly feedback batch at 02:00 IST")
    except ImportError:
        logger.warning(
            "apscheduler not installed — nightly batch disabled. "
            "Install: pip install apscheduler"
        )
    except Exception as exc:
        logger.warning("APScheduler startup failed: %s", exc)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
