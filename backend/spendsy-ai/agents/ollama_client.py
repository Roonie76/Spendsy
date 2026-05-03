import json
import logging
import re
import httpx
from typing import Dict, Any, List
from config import settings

logger = logging.getLogger(__name__)

_CODE_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def _strip_code_fences(text: str) -> str:
    """Ollama models often wrap JSON in ```json ... ``` fences despite format=json.
    Strip them so downstream json.loads() succeeds."""
    if not text:
        return text
    m = _CODE_FENCE_RE.match(text)
    return m.group(1).strip() if m else text.strip()

async def call_ollama(
    model: str,
    prompt: str,
    context: Dict[str, Any],
    options: Dict[str, Any] | None = None,
    system_prompt: str | None = None,
    thinking: bool = False,
) -> str:
    """
    Execute a chat completion request to the local Ollama API (Asynchronously).
    """
    url = f"{settings.ollama_base_url}/api/chat"

    system_instr = system_prompt or "You are TORA, a helpful financial assistant for the Spendsy app. Return ONLY valid JSON."

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instr},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "format": {
            "type": "object",
            "properties": {
                "reasoning": {"type": "string"},
                "answer": {
                    "type": "object",
                    "properties": {
                        "mode": {"type": "string"},
                        "content": {"type": "string"},
                        "Financial Overview": {"type": "string"},
                        "Current Position": {"type": "string"},
                        "Recommended Strategy": {"type": "string"},
                        "Expected Outcome": {"type": "string"}
                    }
                },
                "tool_calls": {
                    "type": "array"
                }
            },
            "required": ["answer"]
        },
        "keep_alive": f"{settings.ollama_keep_alive}s",
        "options": options or {
            "temperature": 0.0,
            "top_p": 0.9,
            "num_predict": 1024,
            "num_ctx": 4096,
            "seed": 42
        },
        "think": bool(thinking)
    }
    
    logger.info(f"Calling local Ollama model (async): {model}")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            content = result.get("message", {}).get("content", "")
            cleaned = _strip_code_fences(content)
            if not cleaned:
                raise RuntimeError(f"Ollama model {model} returned an empty response")
            return cleaned
    except Exception as e:
        logger.error(f"Ollama request failed: {str(e)}")
        raise RuntimeError(f"Ollama request failed: {str(e)}")
