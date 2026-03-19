from __future__ import annotations
import logging
import httpx
import json
import re
from typing import Any

from app.parser import ParserResponse, ParsedTransaction

logger = logging.getLogger(__name__)

class CloudParser:
    """
    Fallback parser using Gemini (via AI-service).
    Triggered only when local Ollama confidence is below threshold.
    """

    def __init__(self) -> None:
        from app.core.config import settings
        self.settings = settings

    def parse(self, text: str, filename: str | None = None) -> ParserResponse:
        logger.info("cloud_parse_start file=%s", filename)
        
        # We reuse the AI-service /insights endpoint as a proxy to Gemini
        # with response_format="json"
        prompt = (
            "Extract bank transactions from the following bank statement text.\n"
            "Return a JSON list of objects with these keys:\n"
            "  date (YYYY-MM-DD), description, amount (float), type (income/expense), balance, debit, credit.\n"
            "Use null for unknown values. Do NOT invent data.\n\n"
            f"TEXT:\n{text[:10000]}" # Cap at 10k for safety
        )

        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.settings.ai_service_url}/insights",
                    json={
                        "prompt": prompt,
                        "response_format": "json"
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
                        "count": len(parsed)
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
