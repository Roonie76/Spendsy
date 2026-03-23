from __future__ import annotations
import logging
import httpx
import json
import re
from typing import Any

from app.core.base_parser import BaseParser
from app.core.schemas import ParserResponse, ParsedTransaction

logger = logging.getLogger(__name__)

class CloudParser(BaseParser):
    """
    Fallback parser using Gemini (via AI-service).
    Triggered only when local Ollama confidence is below threshold.
    """
    @property
    def name(self) -> str:
        return "cloud_gemini"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def priority(self) -> int:
        return 110 # Even lower than local LLM

    def can_handle(self, content: bytes, text: str, **kwargs: Any) -> float:
        """
        Cloud is the ultimate luxury fallback. It can handle anything, 
        but we only want it if others fail or if the document is very messy.
        """
        if not text:
            return 0.0
            
        # If it's very messy (no structure), cloud handles it best
        return 0.45

    def __init__(self) -> None:
        from app.core.config import settings
        self.settings = settings

    def parse(self, content: bytes, text: str, **kwargs: Any) -> ParserResponse:
        filename = kwargs.get("filename")
        logger.info("cloud_parse_start file=%s", filename)
        
        # We reuse the AI-service /insights endpoint as a proxy to Gemini
        # with response_format="json"
        prompt = (
            "Extract bank transactions from the following bank statement text.\n"
            "Return a JSON list of objects with these keys:\n"
            "  - date (YYYY-MM-DD)\n"
            "  - description (full narrative)\n"
            "  - amount (positive float for both income and expense)\n"
            "  - type (strictly 'income' or 'expense')\n"
            "  - balance (float if available, else null)\n"
            "  - confidence (float between 0.0 and 1.0, NEVER null. If unsure, use 0.8)\n"
            "  - debit (float if applicable)\n"
            "  - credit (float if applicable)\n\n"
            "RULES:\n"
            "1. Output strictly valid JSON.\n"
            "2. Never return null for the 'confidence' or 'amount' fields.\n"
            "3. If a date is missing, skip the row.\n"
            "4. Do NOT invent data.\n\n"
            f"TEXT:\n{text[:10000]}" # Cap at 10k for safety
        )

        try:
            import base64
            img_b64 = base64.b64encode(content).decode("utf-8")
            
            # Determine mime type for Gemini
            mime_type = "application/pdf"
            if filename:
                ext = filename.split(".")[-1].lower()
                if ext in ["jpg", "jpeg"]: mime_type = "image/jpeg"
                elif ext == "png": mime_type = "image/png"
                elif ext == "webp": mime_type = "image/webp"

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.settings.ai_service_url}/insights",
                    json={
                        "prompt": prompt,
                        "response_format": "json",
                        "image": img_b64,
                        "image_mime_type": mime_type
                    },
                    headers={"X-Internal-API-Key": self.settings.internal_api_key}
                )
                response.raise_for_status()
                data = response.json()
                
                # AI-service returns { "status": "ok", "output": [...], "raw": "..." }
                tx_list = data.get("output", [])
                if not isinstance(tx_list, list):
                    logger.warning("cloud_parse_error response_not_list")
                    return self._empty_response("cloud_error")

                parsed: list[ParsedTransaction] = []
                for item in tx_list:
                    try:
                        if isinstance(item, dict) and item.get("date"):
                            parsed.append(ParsedTransaction(**{k: v for k, v in item.items() if k in ParsedTransaction.model_fields}))
                    except Exception:
                        continue

                return ParserResponse(
                    status="success" if parsed else "no_transactions",
                    reconciliation_score=0.90 if parsed else 1.0, # Cloud is generally high confidence
                    transactions=parsed,
                    meta={
                        "method": "cloud_gemini",
                        "model_used": "cloud",
                        "count": len(parsed),
                        "parser_name": self.name,
                        "parser_version": self.version,
                    }
                )

        except Exception as e:
            logger.error("cloud_parse_error error=%s", str(e))
            return self._empty_response("cloud_failure")

    def _empty_response(self, status: str) -> ParserResponse:
        return ParserResponse(
            status=status,
            reconciliation_score=0.0,
            transactions=[],
            meta={"method": "cloud_gemini", "model_used": "cloud", "error": True}
        )
