"""
routes_tora.py — Lightweight TORA AI endpoint mounted inside the auth service.

This allows the frontend (VITE_TORA_URL = spendsy-production.up.railway.app)
to reach the local Ollama LLM via the ngrok tunnel without needing a separate
Railway service deployment.
"""
from __future__ import annotations

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger("auth.tora")

router = APIRouter(tags=["tora"])

# Read Ollama base URL from env — same var used by spendsy-ai service.
OLLAMA_BASE_URL = os.environ.get(
    "OLLAMA_BASE_URL", "http://host.docker.internal:11434"
)
OLLAMA_MODEL = os.environ.get("MODEL_GEMMA", "gemma2:2b")

# The ngrok free tier shows an interstitial page unless this header is sent.
NGROK_HEADERS = {"ngrok-skip-browser-warning": "true"}

SYSTEM_PROMPT = (
    "You are TORA, a friendly and concise AI financial assistant for the Spendsy app. "
    "Help the user understand their spending, savings, and financial health. "
    "Keep answers short and actionable. Do not use markdown unless asked."
)


class ToraRequest(BaseModel):
    question: str
    user_id: int = 0
    model: str | None = None
    tier: str | None = None


class ToraResponse(BaseModel):
    answer: dict


@router.post("/ask-tora", response_model=ToraResponse)
async def ask_tora(payload: ToraRequest):
    if not payload.question or not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    model = payload.model or OLLAMA_MODEL
    url = f"{OLLAMA_BASE_URL}/api/chat"

    request_body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": payload.question.strip()},
        ],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 512,
            "num_ctx": 2048,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=request_body, headers=NGROK_HEADERS)
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "").strip()
            if not content:
                raise ValueError("Empty response from model")

        return ToraResponse(answer={"mode": "chat", "content": content})

    except httpx.ConnectError:
        logger.error("Cannot connect to Ollama at %s", OLLAMA_BASE_URL)
        raise HTTPException(
            status_code=503,
            detail="AI service is unreachable. Make sure your ngrok tunnel is running.",
        )
    except httpx.TimeoutException:
        logger.error("Ollama request timed out")
        raise HTTPException(status_code=504, detail="AI response timed out. Try a shorter question.")
    except Exception as exc:
        logger.error("TORA error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/tora-health")
async def tora_health():
    """Quick check: is Ollama reachable via the configured URL?"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags", headers=NGROK_HEADERS)
            r.raise_for_status()
            models = [m.get("name") for m in r.json().get("models", [])]
            return {"ok": True, "ollama_url": OLLAMA_BASE_URL, "models": models}
    except Exception as exc:
        return {"ok": False, "ollama_url": OLLAMA_BASE_URL, "error": str(exc)}
