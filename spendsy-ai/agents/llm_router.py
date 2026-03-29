import logging
from typing import Dict, Any
from .gemini_client import call_gemini
from .gemini_client import call_gemini
from .mistral_client import call_mistral

logger = logging.getLogger(__name__)

def call_llm(model: str, prompt: str, context: Dict[str, Any]) -> str:
    """
    Route the prompt to the appropriate LLM client based on the model branding.
    Maps:
    - 'tora' -> mistral (base)
    - 'tora_plus' -> gemini (advanced)
    """
    logger.info(f"Routing request to model branding: {model}")
    
    m = model.lower()
    if m == "tora_plus":
        return call_gemini(prompt, context)
    
    # Default to TORA (Mistral)
    return call_mistral(prompt, context)
