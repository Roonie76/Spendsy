from __future__ import annotations

import httpx

from ..core.config import settings


def parse_statement(pdf_bytes: bytes, filename: str) -> dict:
    url = f"{settings.parser_service_url.rstrip('/')}/parse"
    files = {"file": (filename, pdf_bytes, "application/pdf")}
    with httpx.Client(timeout=45.0) as client:
        response = client.post(url, files=files)
    response.raise_for_status()
    return response.json()
