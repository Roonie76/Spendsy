from __future__ import annotations

import httpx

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


def parse_statement(file_bytes: bytes, filename: str, content_type: str | None = None) -> dict:
    url = f"{settings.parser_service_url.rstrip('/')}/parse"
    mime_type = _guess_content_type(filename, content_type)
    files = {"file": (filename, file_bytes, mime_type)}
    with httpx.Client(timeout=45.0) as client:
        response = client.post(url, files=files)
    response.raise_for_status()
    return response.json()
