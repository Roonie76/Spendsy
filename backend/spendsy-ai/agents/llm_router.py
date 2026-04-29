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


def call_llm(
    model_branding: str,
    prompt: str,
    context: Dict[str, Any],
    system_prompt: str | None = None,
    thinking: bool = False,
) -> str:
    """
    Route the prompt to local Ollama models.

    Chain: primary (model_gemma) → fallback (model_llama) → error.

    Args:
        thinking: If True, enable gemma4's thinking mode on the primary model.
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

        time.sleep(2)
        logger.info(f"Fallback to {settings.model_llama}")

        try:
            fallback_response = call_ollama(
                settings.model_llama, prompt, context,
                system_prompt=system_prompt,
            )
            try:
                json.loads(fallback_response)
            except json.JSONDecodeError:
                logger.warning(f"Fallback {settings.model_llama} returned invalid JSON, passing through")
            return fallback_response

        except Exception as fe:
            logger.error(f"Fallback ({settings.model_llama}) also failed: {fe}")

            # Surface actionable diagnostics
            health = check_ollama_health()
            if not health["ok"]:
                raise RuntimeError(
                    f"Ollama unreachable at {settings.ollama_base_url}. "
                    f"Ensure Ollama is running: 'ollama serve'. Error: {health['error']}"
                )
            else:
                available = health["models"]
                if primary_model not in available and settings.model_llama not in available:
                    raise RuntimeError(
                        f"Ollama is running but required models not found. "
                        f"Available: {available}. "
                        f"Run: 'ollama pull {primary_model}' and 'ollama pull {settings.model_llama}'"
                    )

            raise RuntimeError(f"All LLM tiers failed. Primary error: {e}")
