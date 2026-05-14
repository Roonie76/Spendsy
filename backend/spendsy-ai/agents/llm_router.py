import logging
import json
import asyncio
import httpx
from typing import Dict, Any
from config import settings
from .ollama_client import call_ollama

logger = logging.getLogger(__name__)


async def check_ollama_health() -> dict:
    """Quick connectivity check against Ollama. Returns status dict."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            headers = {"ngrok-skip-browser-warning": "true"}
            response = await client.get(f"{settings.ollama_base_url}/api/tags", headers=headers)
            response.raise_for_status()
            data = response.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return {"ok": True, "models": models}
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def call_gemini(prompt: str, system_prompt: str | None = None) -> str:
    """Tertiary cloud fallback via Google Gemini (Async)."""
    api_key = settings.google_api_key
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not configured for cloud fallback")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    
    system_instr = system_prompt or "You are TORA, a helpful financial assistant for the Spendsy app."
    
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": f"System Instructions: {system_instr}\n\nUser Query: {prompt}"}]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "topP": 0.95,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json"
        }
    }

    logger.info("Calling Gemini cloud fallback (async)")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not text:
            raise RuntimeError("Gemini returned empty response")
        return text


async def call_llm(
    model_branding: str,
    prompt: str,
    context: Dict[str, Any],
    system_prompt: str | None = None,
    thinking: bool = False,
) -> str:
    """
    Route the prompt to local Ollama models with cloud fallback (Async).
    """
    logger.info(f"Routing request to model branding: {model_branding}")

    branding = model_branding.lower()
    primary_model = settings.model_gemma

    try:
        response = await call_ollama(
            primary_model, prompt, context,
            system_prompt=system_prompt, thinking=thinking,
        )
        json.loads(response)
        return response

    except (Exception, json.JSONDecodeError) as e:
        logger.warning(f"Primary model ({primary_model}) failed: {e}")

        # Try Ollama fallback
        if settings.model_llama and settings.model_llama != primary_model:
            await asyncio.sleep(0.5) # Reduced sleep
            logger.info(f"Fallback to {settings.model_llama}")
            try:
                fallback_response = await call_ollama(
                    settings.model_llama, prompt, context,
                    system_prompt=system_prompt,
                )
                json.loads(fallback_response)
                return fallback_response
            except Exception as fe:
                logger.warning(f"Ollama fallback ({settings.model_llama}) also failed: {fe}")

        # Final attempt: Cloud fallback
        logger.info("Initiating cloud fallback to Gemini")
        try:
            return await call_gemini(prompt, system_prompt=system_prompt)
        except Exception as ge:
            logger.error(f"Cloud fallback (Gemini) also failed: {ge}")
            raise RuntimeError(f"All LLM tiers failed. Primary error: {e}, Cloud error: {ge}")
