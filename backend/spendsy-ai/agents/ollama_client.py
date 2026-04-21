import json
import logging
import re
import urllib.request
import urllib.error
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

def call_ollama(
    model: str,
    prompt: str,
    context: Dict[str, Any],
    options: Dict[str, Any] | None = None,
    system_prompt: str | None = None,
) -> str:
    """
    Execute a chat completion request to the local Ollama API.

    Args:
        model: The name of the Ollama model (e.g., 'phi3:mini', 'qwen2.5:7b')
        prompt: The user-role content (the current question + grounded data)
        context: Financial context (unused in raw HTTP call but kept for interface consistency)
        options: Optional Ollama generation parameters
        system_prompt: Optional full system prompt (TORA rules, schema, etc). Falls
            back to a minimal default when not supplied.
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
        "format": "json",
        "keep_alive": f"{settings.ollama_keep_alive}s",  # Unload immediately if 0
        "options": options or {
            "temperature": 0.0,
            "top_p": 0.9,
            "num_predict": 2048,
            "num_ctx": 8192,
            "seed": 42
        },
        "think": False
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(payload).encode('utf-8'), 
        headers=headers, 
        method="POST"
    )
    
    logger.info(f"Calling local Ollama model: {model}")
    
    try:
        with urllib.request.urlopen(req, timeout=300.0) as response:
            result = json.loads(response.read().decode('utf-8'))
            content = result.get("message", {}).get("content", "")
            cleaned = _strip_code_fences(content)
            if not cleaned:
                raise RuntimeError(f"Ollama model {model} returned an empty response")
            return cleaned
    except urllib.error.URLError as e:
        logger.error(f"Ollama connection error: {e.reason}")
        raise RuntimeError(f"Ollama connection error: {e.reason}")
    except Exception as e:
        logger.error(f"Ollama request failed: {str(e)}")
        raise RuntimeError(f"Ollama request failed: {str(e)}")
