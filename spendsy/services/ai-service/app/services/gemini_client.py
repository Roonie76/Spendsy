from __future__ import annotations

import json

import httpx

from ..core.config import settings


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


def generate_text(prompt: str, *, response_format: str = "text") -> str:
    api_key = settings.gemini_api_key
    if not api_key:
        raise GeminiError("GEMINI_API_KEY is not configured")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    generation_config: dict = {"temperature": 0.4}
    if response_format == "json":
        generation_config["response_mime_type"] = "application/json"
        generation_config["temperature"] = 0.2

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
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
        if response.status_code >= 500:
            response.raise_for_status()
        if response.status_code >= 400:
            # Let 4xx pass without retry except maybe some transient GCP errors if any
            response.raise_for_status()
        return response

    try:
        response = _do_generate()
    except Exception as exc:
        raise GeminiError("Gemini API request failed") from exc

    data = response.json()
    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
    if not text:
        raise GeminiError("Gemini API returned empty response")
    return text
