from __future__ import annotations
import logging
import time
from typing import Any

from app.core.extractors import get_extractor
from app.core.quality import QualityDetector, ContentQuality
from app.core.reconciliation import ReconciliationEngine
from app.core.routers import ParsingRouter, ParsingStrategy
from app.core.regex_parser import parse_structured_text
from app.parser import IntegratedParser, LLMParser, ParsedTransaction, ParserResponse

logger = logging.getLogger(__name__)


class DocumentParserPipeline:
    def __init__(self) -> None:
        self.quality_detector = QualityDetector()
        self.router = ParsingRouter()
        self.table_parser = IntegratedParser()   # handles CSV / XLSX / PDF tables
        self.llm_parser = LLMParser()

    def run(self, content: bytes, filename: str, content_type: str) -> Any:
        start_time = time.time()
        logger.info("pipeline_start file=%s", filename)

        # Stage 1 — Text Extraction
        extractor = get_extractor(content_type, filename)
        text = extractor.extract(content)
        logger.info("pipeline_stage=extract chars=%d", len(text))

        # Stage 2 — Quality Detection
        quality = self.quality_detector.detect(text)
        logger.info("pipeline_stage=quality result=%s", quality)

        # Stage 3 — Routing
        strategy = self.router.route(quality, filename)
        logger.info("pipeline_stage=route strategy=%s", strategy)

        # Stage 4 — Parsing
        if strategy == ParsingStrategy.REGEX and not _is_binary_format(filename):
            # Fast regex path: plain-text structured statements
            result = self._run_regex(text, filename)
        elif strategy == ParsingStrategy.TABULAR:
            # Explicit tabular path (CSV/XLSX/XLS)
            result = self.table_parser.parse(content, filename=filename, content_type=content_type)
        elif strategy == ParsingStrategy.LLM:
            result = self.llm_parser.parse(text, filename=filename)
            
            # Smart Fallback: if local LLM confidence is low, try Cloud LLM
            confidence = result.meta.get("confidence_score", 0.0)
            if confidence < self.llm_parser.settings.llm_confidence_threshold:
                logger.warning("llm_confidence_low (%.4f) triggering cloud fallback", confidence)
                from app.parsers.cloud_parser import CloudParser
                cloud_parser = CloudParser()
                cloud_result = cloud_parser.parse(text, filename=filename)
                
                # Merge or replace? For simplicity, we replace with cloud if it found more/better data
                if len(cloud_result.transactions) >= len(result.transactions):
                    result = cloud_result
                    logger.info("llm_fallback_success model=cloud txns=%d", len(result.transactions))
        else:
            # HYBRID or any remaining format → table parser
            result = self.table_parser.parse(content, filename=filename, content_type=content_type)

        # Stage 5 — Reconciliation
        reconciler = ReconciliationEngine()
        recon_result = reconciler.reconcile(result.transactions)
        
        # Apply corrections and update scores
        result.transactions = recon_result.corrected_transactions
        result.reconciliation_score = recon_result.reconciliation_score
        
        logger.info("pipeline_stage=reconciliation result=%s score=%.4f errors=%d",
                    recon_result.status, recon_result.reconciliation_score, len(recon_result.errors))

        processing_time = time.time() - start_time
        logger.info("pipeline_done file=%s strategy=%s time=%.2fs txns=%d model=%s",
                    filename, strategy, processing_time, len(result.transactions), 
                    result.meta.get("model_used", "regex/table"))

        result.meta.update({
            "pipeline_strategy": str(strategy),
            "content_quality": str(quality),
            "reconciliation_status": recon_result.status,
            "reconciliation_errors": [e.message for e in recon_result.errors],
            "processing_time_seconds": round(processing_time, 3),
        })
        return result

    # ------------------------------------------------------------------
    def _run_regex(self, text: str, filename: str) -> ParserResponse:
        """Use the high-performance regex parser for plain-text structured rows."""
        from datetime import date as _date

        raw_txns = parse_structured_text(text)
        parsed: list[ParsedTransaction] = []
        for t in raw_txns:
            try:
                tx_date = _date.fromisoformat(t.date)
            except ValueError:
                continue

            amount = t.debit or t.credit or 0.0
            if amount <= 0:
                continue

            parsed.append(ParsedTransaction(
                date=tx_date,
                description=t.description,
                amount=float(t.debit or t.credit or 0.0),
                type="expense" if t.debit is not None else "income",
                debit=t.debit,
                credit=t.credit,
                balance=t.balance,
                confidence=0.95,  # regex‐parsed rows are highly reliable
                is_valid=True,
            ))

        return ParserResponse(
            status="success" if parsed else "no_transactions",
            reconciliation_score=0.99 if parsed else 1.0,
            transactions=parsed,
            meta={"method": "regex_structured", "bank": "generic", "count": len(parsed)},
        )


def _is_binary_format(filename: str) -> bool:
    fn = filename.lower()
    return fn.endswith((".pdf", ".xlsx", ".xls"))
