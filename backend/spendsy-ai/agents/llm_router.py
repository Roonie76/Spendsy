import logging
import json
import time
from typing import Dict, Any
from config import settings
from .ollama_client import call_ollama

logger = logging.getLogger(__name__)


def check_ollama_health() -> dict:
    """Quick connectivity check against Ollama. Returns status dict."""
    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(f"{settings.ollama_base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode())
            models = [m.get("name", "") for m in data.get("models", [])]
            return {"ok": True, "models": models}
    except urllib.error.URLError as e:
        return {"ok": False, "error": f"Connection refused: {e.reason}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def call_gemini(prompt: str, system_prompt: str | None = None) -> str:
    """Tertiary cloud fallback via Google Gemini."""
    import urllib.request
    import json
    
    api_key = settings.google_api_key
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY not configured for cloud fallback")

    # Use 2.5-flash-lite to match the established pattern in legacy service
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

    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    
    logger.info("Calling Gemini cloud fallback")
    with urllib.request.urlopen(req, timeout=30.0) as resp:
        data = json.loads(resp.read().decode())
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not text:
            raise RuntimeError("Gemini returned empty response")
        return text


def call_llm(
    model_branding: str,
    prompt: str,
    context: Dict[str, Any],
    system_prompt: str | None = None,
    thinking: bool = False,
) -> str:
    """
    Route the prompt to local Ollama models with cloud fallback.

    Chain: primary (model_gemma) → fallback (model_llama) → cloud (Gemini) → error.
    """
    logger.info(f"Routing request to model branding: {model_branding}")

    branding = model_branding.lower()
    if branding == "tora_plus":
        logger.warning("TORA+ requested but not yet available — falling back to TORA")

    primary_model = settings.model_gemma

    try:
        response = call_ollama(
            primary_model, prompt, context,
            system_prompt=system_prompt, thinking=thinking,
        )
        json.loads(response)
        logger.info(f"Valid JSON from {primary_model}")
        return response

    except (Exception, json.JSONDecodeError) as e:
        logger.warning(f"Primary model ({primary_model}) failed: {e}")

        # Try Ollama fallback
        if settings.model_llama and settings.model_llama != primary_model:
            time.sleep(1)
            logger.info(f"Fallback to {settings.model_llama}")
            try:
                fallback_response = call_ollama(
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
            return call_gemini(prompt, system_prompt=system_prompt)
        except Exception as ge:
            logger.error(f"Cloud fallback (Gemini) also failed: {ge}")

            # Surface actionable diagnostics for Ollama if cloud also failed
            health = check_ollama_health()
            if not health["ok"]:
                raise RuntimeError(
                    f"Ollama unreachable and Cloud fallback failed. "
                    f"Ensure Ollama is running or check your internet/API key. "
                    f"Ollama error: {health['error']}"
                )
            else:
                available = health["models"]
                if primary_model not in available:
                    raise RuntimeError(
                        f"Ollama is running but models not found and Cloud fallback failed. "
                        f"Pull models or check API key. Available models: {available}"
                    )

            raise RuntimeError(f"All LLM tiers failed. Primary error: {e}, Cloud error: {ge}")
