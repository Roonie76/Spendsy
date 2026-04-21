from __future__ import annotations

import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("ai.gemini")


class GeminiError(RuntimeError):
    pass


def build_prompt(prompt: str, context: str | dict | list | None) -> str:
    if context is None:
        return prompt
    if isinstance(context, (dict, list)):
        context_str = json.dumps(context, ensure_ascii=False)
    else:
        context_str = str(context)
    return f"{prompt}\n\nCONTEXT:\n{context_str}"


def generate_text(prompt: str, *, response_format: str = "text", image: str | None = None, image_mime_type: str | None = None) -> str:
    api_key = settings.gemini_api_key or settings.google_api_key
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-lite:generateContent?key={api_key}" # Switched back to 2.5-flash-lite on v1beta
    )
    # Security: Only log the start and end of the key for verification
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if api_key else "NONE"
    logger.debug("Using Model: gemini-2.5-flash-lite | API Key: %s", masked_key)
    generation_config: dict = {"temperature": 0.4}
    
    # Use prompt enforcement for JSON on stable v1 to avoid 'response_mime_type' errors
    effective_prompt = prompt
    if response_format == "json":
        generation_config["temperature"] = 0.1
        effective_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON. No markdown backticks, no preamble."

    parts = [{"text": effective_prompt}]
    if image and image_mime_type:
        parts.append({
            "inline_data": {
                "mime_type": image_mime_type,
                "data": image
            }
        })

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": generation_config,
    }


    from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError)),
    )
    def _do_generate():
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, json=payload)
        
        if response.status_code != 200:
            error_body = response.text
            logger.error("Gemini API Error Response (Status %d): %s", response.status_code, error_body)
            # Raise with body included
            raise GeminiError(f"API Error {response.status_code}: {error_body}")
            
        return response

    try:
        response = _do_generate()
    except Exception as exc:
        # If it was wrapped by Tenacity, try to get the original if possible
        errorMessage = str(exc)
        logger.error("Final AI Failure: %s", errorMessage)
        raise GeminiError(errorMessage) from exc

    data = response.json()
    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
    if not text:
        raise GeminiError("Gemini API returned empty response")
    return text
