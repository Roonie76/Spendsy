from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from agents.tora_agent import handle_user_question
from config import settings
from tiering import TieringConfig
import httpx
import logging

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


class QuestionRequest(BaseModel):
    user_id: int = 1
    question: str
    model: str | None = None  # Optional; will be auto-selected based on tier if None
    tier: str | None = None   # Optional; will be auto-fetched if None

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "spendsy-ai"}


async def fetch_user_tier(user_id: int) -> str:
    """
    Fetch user tier from finance-service internal API.
    Falls back to 'free' if unavailable.
    """
    try:
        url = f"{settings.finance_service_url}/internal/user-profile/{user_id}"
        headers = {"X-Internal-API-Key": settings.internal_api_key}
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                tier = data.get("data", {}).get("tier", "free")
                logger.info(f"Fetched tier '{tier}' for user {user_id}")
                return tier
    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching tier for user {user_id}, defaulting to 'free'")
    except Exception as e:
        logger.warning(f"Error fetching tier for user {user_id}: {e}, defaulting to 'free'")
    
    return "free"  # Safe default


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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
