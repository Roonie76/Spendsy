from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import UserContext, get_current_user
from app.schemas import AIRequest, AIResponse, HealthResponse
from app.services.gemini_client import GeminiError, build_prompt, generate_text

router = APIRouter(tags=["ai"])


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", service="ai-service")


def _run_gemini(payload: AIRequest) -> AIResponse:
    prompt = build_prompt(payload.prompt, payload.context)
    try:
        raw = generate_text(prompt, response_format=payload.response_format)
    except GeminiError as exc:
        print(f"ERROR: AI Request failed: {str(exc)}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    output: str | dict | list = raw
    if payload.response_format == "json":
        try:
            # Robust JSON extraction
            content = raw.strip()
            if content.startswith("```"):
                # Handle markdown code blocks
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            
            output = json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            print(f"ERROR: JSON Parsing failed for raw output: {raw[:100]}... Error: {str(e)}")
            output = []
    return AIResponse(status="ok", output=output, raw=raw)


@router.post("/insights", response_model=AIResponse)
def insights(payload: AIRequest, _: UserContext = Depends(get_current_user)):
    return _run_gemini(payload)


@router.post("/health-score", response_model=AIResponse)
def health_score(payload: AIRequest, _: UserContext = Depends(get_current_user)):
    return _run_gemini(payload)


@router.post("/forecast", response_model=AIResponse)
def forecast(payload: AIRequest, _: UserContext = Depends(get_current_user)):
    return _run_gemini(payload)
