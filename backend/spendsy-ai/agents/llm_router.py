import logging
import json
from typing import Dict, Any
from config import settings
from .ollama_client import call_ollama
from .gemini_client import call_gemini  # Kept as deep fallback
from .mistral_client import call_mistral # Kept as deep fallback

logger = logging.getLogger(__name__)

def call_llm(
    model_branding: str,
    prompt: str,
    context: Dict[str, Any],
    system_prompt: str | None = None,
    thinking: bool = False,
) -> str:
    """
    Route the prompt to specialized local models via Ollama with reasoning fallback.

    Logic:
    - 'tora' -> primary local model (see settings.model_gemma)
    - 'tora_plus' -> DISABLED (pending fine-tuning)
    - Fallback -> settings.model_llama, then Mistral Cloud if configured

    Args:
        thinking: If True, enable gemma4's thinking mode on the primary model.
            Gated by the caller based on query complexity (track 2 decisions).
            Fallback model does NOT use thinking — when the primary failed,
            we want the fastest-possible recovery path.
    """
    logger.info(f"Routing request to model branding: {model_branding}")
    logger.info(f"LLM Prompt: {prompt}")

    branding = model_branding.lower()

    if branding == "tora_plus":
        logger.warning("TORA+ requested but not yet available — falling back to TORA")

    primary_model = settings.model_gemma

    try:
        response = call_ollama(
            primary_model, prompt, context,
            system_prompt=system_prompt, thinking=thinking,
        )
        logger.info(f"Primary model raw response: {response}")
        json.loads(response)
        logger.info(f"Successfully received valid JSON from {primary_model}")
        return response

    except (Exception, json.JSONDecodeError) as e:
        logger.warning(f"Primary model ({primary_model}) failed or returned invalid JSON: {e}")

        import time
        logger.info(f"Cooling down for 2 seconds to ensure {primary_model} is unloaded...")
        time.sleep(2)

        logger.info(f"Triggering reasoning fallback to {settings.model_llama}")

        try:
            fallback_response = call_ollama(settings.model_llama, prompt, context, system_prompt=system_prompt)
            logger.info(f"Fallback model raw response: {fallback_response}")
            try:
                json.loads(fallback_response)
                logger.info(f"Successfully received valid JSON from fallback model {settings.model_llama}")
            except json.JSONDecodeError:
                logger.warning(f"Fallback model {settings.model_llama} returned invalid JSON, but returning it for agent recovery")
            return fallback_response

        except Exception as fe:
            logger.error(f"Fallback model ({settings.model_llama}) also failed: {fe}")

            if settings.mistral_api_key:
                logger.info("Ultimate fallback: dashboarding to Mistral Cloud")
                return call_mistral(prompt, context)

            raise RuntimeError(f"All LLM tiers failed to provide a valid response. Original error: {e}")
