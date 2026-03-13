from __future__ import annotations

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from ..core.config import settings


def _guess_content_type(filename: str, provided: str | None = None) -> str:
    lowered = (provided or "").lower().strip()
    if lowered:
        return lowered
    if filename.lower().endswith(".csv"):
        return "text/csv"
    if filename.lower().endswith(".xlsx"):
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return "application/pdf"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError)),
)
def parse_statement(file_bytes: bytes, filename: str, content_type: str | None = None) -> dict:
    url = f"{settings.parser_service_url.rstrip('/')}/parse"
    mime_type = _guess_content_type(filename, content_type)
    files = {"file": (filename, file_bytes, mime_type)}
    with httpx.Client(timeout=300.0) as client:
        response = client.post(url, files=files)
    
    # raise_for_status will throw HTTPStatusError which triggers the retry if it's a 5xx
    if response.status_code >= 500:
        response.raise_for_status()
    # Let 4xx errors pass through (e.g validation error) without retrying, as they will just fail again
    if response.status_code >= 400:
        response.raise_for_status()

    return response.json()
