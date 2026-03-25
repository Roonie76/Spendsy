from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings


def _guess_content_type(filename: str, provided: str | None = None) -> str:
    lowered = (provided or "").lower().strip()
    if lowered:
        return lowered
    if filename.lower().endswith(".csv"):
        return "text/csv"
    if filename.lower().endswith(".xlsx"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "application/pdf"


def _is_retryable(e: Exception) -> bool:
    if isinstance(e, (httpx.ConnectError, httpx.TimeoutException)):
        return True
    if isinstance(e, httpx.HTTPStatusError):
        return e.response.status_code >= 500 or e.response.status_code == 429
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception(_is_retryable),
)
def parse_statement(file_bytes: bytes, filename: str, content_type: str | None = None, user_id: int | str = "anonymous") -> dict:
    url = f"{settings.parser_service_url.rstrip('/')}/parse"
    params = {"user_id": str(user_id)}
    mime_type = _guess_content_type(filename, content_type)
    files = {"file": (filename, file_bytes, mime_type)}
    headers = {"X-Internal-API-Key": settings.internal_api_key}
    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(url, params=params, files=files, headers=headers)
            
        if response.status_code >= 400:
            # For 5xx errors, we still want to raise so tenacity can retry if applicable
            if response.status_code >= 500:
                response.raise_for_status()
                
            try:
                error_detail = response.json().get("detail", "Internal Parser Error")
            except Exception:
                error_detail = response.text or "Internal Parser Error"
                
            return {
                "status": "error",
                "error": error_detail,
                "http_status": response.status_code
            }

        return response.json()
    except httpx.HTTPStatusError as exc:
        # This will be caught if response.raise_for_status() was called above (for 5xx)
        # We let it bubble up for Tenacity to retry, OR return it if it's the final attempt.
        # However, for simplicity in the first pass, we'll catch common request errors here.
        raise exc 
    except httpx.RequestError as exc:
        return {
            "status": "error",
            "error": f"Could not connect to parser service: {str(exc)}",
            "http_status": 503
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": f"Unexpected parser client error: {str(exc)}",
            "http_status": 500
        }
