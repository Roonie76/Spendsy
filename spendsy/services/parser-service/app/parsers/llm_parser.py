from __future__ import annotations

import json
import logging
import re
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.base_parser import BaseParser
from app.core.schemas import ParsedTransaction, ParserResponse

logger = logging.getLogger(__name__)

class LLMParser(BaseParser):
    """
    Production-grade LLM parser backed by a local Ollama model.
    Handles unstructured documents by chunking text and extracting transactions as JSON.
    """
    @property
    def name(self) -> str:
        return "llm_local"

    @property
    def version(self) -> str:
        return "1.2.0"

    @property
    def priority(self) -> int:
        return 100

    def can_handle(self, content: bytes, text: str, **kwargs: Any) -> float:
        """
        LLM is the ultimate catch-all. 
        It scores higher if text is unstructured but not empty.
        """
        if not text:
            return 0.0
        
        # If it's very short, LLM is good
        if len(text) < 1000:
            return 0.5
            
        # Base fallback score
        return 0.4

    _CHUNK_SIZE = 1200
    _MAX_CHUNKS = 8
    _JSON_RETRIES = 3
    _TIMEOUT = 120.0

    _PROMPT_TEMPLATE = (
        "You are a financial data extraction assistant.\n"
        "Extract ALL bank transactions from the text below.\n"
        "Return ONLY a valid JSON array (no markdown, no explanation).\n"
        "Each element must have these exact keys:\n"
        '  "date" (YYYY-MM-DD), "description" (string), "amount" (number > 0),\n'
        '  "type" ("income" or "expense"), "balance" (number or null),\n'
        '  "debit" (number or null), "credit" (number or null)\n'
        "Do NOT invent values. Use null for unknown fields.\n\n"
        "TEXT:\n{chunk}\n\n"
        "JSON ARRAY:"
    )

    def __init__(self) -> None:
        from app.core.config import settings
        self.settings = settings
        self._base_url = settings.ollama_base_url
        self._primary = settings.ollama_primary_model
        self._fallback = settings.ollama_fallback_model

    def parse(self, content: bytes, text: str, **kwargs: Any) -> ParserResponse:
        filename = kwargs.get("filename")
        logger.info("llm_parse_start file=%s", filename)

        sanitized = self._sanitize_text(text)
        if not sanitized:
            return ParserResponse(
                status="empty_content",
                reconciliation_score=1.0,
                transactions=[],
                meta={"method": "llm_local", "notice": "No extractable text found"}
            )

        chunks = self._chunk_text(sanitized)
        logger.info("llm_parse chunks=%d file=%s", len(chunks), filename)

        # Try primary model
        transactions, model_used = self._parse_with_model(chunks, self._primary)

        # Fallback if primary produced nothing
        if not transactions and self._fallback and self._fallback != self._primary:
            logger.info("llm_parse primary_empty_fallback model=%s", self._fallback)
            transactions, model_used = self._parse_with_model(chunks, self._fallback)

        confidence = self._compute_confidence(transactions, len(chunks))

        logger.info(
            "llm_parse_done file=%s model=%s txns=%d confidence=%.4f",
            filename, model_used, len(transactions), confidence
        )

        return ParserResponse(
            status="success" if transactions else "no_transactions",
            reconciliation_score=round(confidence, 4),
            transactions=transactions,
            meta={
                "method": "llm_local",
                "model_used": model_used,
                "confidence_score": round(confidence, 4),
                "count": len(transactions),
                "chunks_processed": len(chunks),
                "parser_name": self.name,
                "parser_version": self.version,
            }
        )

    def _parse_with_model(self, chunks: list[str], model: str) -> tuple[list[ParsedTransaction], str]:
        all_txns: list[ParsedTransaction] = []
        seen_keys: set[tuple] = set()

        for chunk in chunks:
            prompt = self._PROMPT_TEMPLATE.format(chunk=chunk)
            raw_json = self._call_ollama_with_retry(prompt, model)
            if not raw_json:
                continue

            for tx in self._parse_raw_json(raw_json):
                # Simple dedup within the session
                key = (tx.date.isoformat(), tx.description.lower()[:60], round(float(tx.amount), 2))
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_txns.append(tx)

        return all_txns, model

    def _call_ollama_with_retry(self, prompt: str, model: str) -> str | None:
        for attempt in range(1, self._JSON_RETRIES + 1):
            raw = self._call_ollama(prompt, model)
            if raw is None:
                continue

            cleaned = self._clean_json(raw)
            if self._is_valid_json_array(cleaned):
                return cleaned

            logger.debug("ollama_retry attempt=%d model=%s invalid_json", attempt, model)

        logger.debug("ollama_retry_failed model=%s", model)
        return None

    def _call_ollama(self, prompt: str, model: str) -> str | None:
        url = f"{self._base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 2048}
        }
        try:
            logger.debug("ollama_request model=%s prompt=%s", model, prompt[:100])
            with httpx.Client(timeout=self._TIMEOUT) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                response_text = resp.json().get("response")
                logger.debug("ollama_response_raw model=%s text=%s", model, response_text[:200] if response_text else "None")
                return response_text
        except Exception as e:
            logger.error("ollama_error model=%s error=%s", model, str(e))
            return None

    def _parse_raw_json(self, raw_json: str) -> list[ParsedTransaction]:
        try:
            logger.debug("ollama_parsing_json raw=%s", raw_json[:200])
            items = json.loads(raw_json)
            if not isinstance(items, list):
                if isinstance(items, dict) and "transactions" in items:
                    items = items["transactions"]
                else:
                    logger.debug("ollama_parse_json_error raw=%s error=%s", raw_json[:200], "Not a list or dict with 'transactions'")
                    return []
        except (json.JSONDecodeError, ValueError) as e:
            logger.debug("ollama_parse_json_error raw=%s error=%s", raw_json[:200], e)
            return []

        parsed: list[ParsedTransaction] = []
        for item in items:
            if not isinstance(item, dict):
                logger.debug("ollama_parse_json_item_error item=%s error=%s", str(item)[:100], "Not a dictionary")
                continue
            try:
                # Basic normalization
                if "date" in item and isinstance(item["date"], str):
                    # Pydantic handles the rest
                    parsed.append(ParsedTransaction(**{k: v for k, v in item.items() if k in ParsedTransaction.model_fields}))
            except Exception as e:
                logger.debug("ollama_parse_json_item_error item=%s error=%s", str(item)[:100], e)
                continue
        return parsed

    def _chunk_text(self, text: str) -> list[str]:
        if len(text) <= self._CHUNK_SIZE:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text) and len(chunks) < self._MAX_CHUNKS:
            end = min(start + self._CHUNK_SIZE, len(text))
            if end < len(text):
                # Avoid splitting mid-line
                newline = text.rfind("\n", start, end)
                if newline > start:
                    end = newline + 1
            chunks.append(text[start:end])
            start = end
        return chunks

    def _compute_confidence(self, transactions: list[ParsedTransaction], n_chunks: int) -> float:
        """
        Confidence (0.0 - 1.0) based on:
        - JSON validity (implied if we got txns) : 0.4
        - Extraction density (txns / chunk)      : 0.3
        - Field ratio (missing fields)           : 0.3
        """
        if not transactions:
            return 0.0

        # Field completeness
        total_fields = len(transactions) * 4  # date, desc, amt, type
        filled_fields = sum(
            (1 if tx.date else 0) + (1 if tx.description else 0) + (1 if tx.amount > 0 else 0) + (1 if tx.type else 0)
            for tx in transactions
        )
        field_ratio = filled_fields / total_fields if total_fields > 0 else 0

        # Density: at least 1 txn per chunk is good
        density_ratio = min(1.0, len(transactions) / max(1, n_chunks))

        score = 0.4 + (density_ratio * 0.3) + (field_ratio * 0.3)
        return min(1.0, score)

    def _sanitize_text(self, text: str) -> str:
        if not text:
            return ""
        cleaned = text.replace("\x00", " ")
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:15000]

    def _clean_json(self, raw: str) -> str:
        if not raw:
            return "[]"
        # Strip <think> tags from deepseek models
        raw = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE).strip()
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
        if match:
            return match.group(1).strip()
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end > start:
            return raw[start: end + 1].strip()
        return raw.strip()

    def _is_valid_json_array(self, s: str) -> bool:
        try:
            val = json.loads(s)
            return isinstance(val, (list, dict))
        except (json.JSONDecodeError, ValueError):
            return False
