from __future__ import annotations

import asyncio
import time
import logging
import functools
from typing import Any

from app.core.schemas import ParserResponse
from app.core.registry import ParserRegistry
from app.core.extractors import get_extractor
from app.core.format_detector import FormatDetector
from app.core.reconciliation import CrossParserReconciler
from app.core.validator import TransactionValidator
from app.core.categorizer import TransactionCategorizer
from app.core.header_extractor import HeaderExtractor
from app.core.observability import metrics, sla_tracker, cost_guard
from app.core.safety import safety_manager
from app.core.config import settings

logger = logging.getLogger(__name__)

class DocumentParserPipeline:
    """
    Orchestrates the bank statement parsing process across multiple strategies.
    Now includes granular safety switches, cost guardrails, and bank-level metrics.
    """
    def __init__(self):
        self.detector = FormatDetector()
        self.reconciler = CrossParserReconciler()
        self.validator = TransactionValidator()
        self.categorizer = TransactionCategorizer()
        self.header_extractor = HeaderExtractor()

    async def run(self, content: bytes, **kwargs: Any) -> ParserResponse:
        start_time = time.time()
        filename = kwargs.get("filename", "unknown.pdf")
        content_type = kwargs.get("content_type", "application/pdf")
        user_id = kwargs.get("user_id", "anonymous")
        tier = kwargs.get("tier", "free")
        
        # ── Stage 1: Extraction ────────────────────────────────────────
        try:
            extractor = get_extractor(content_type, filename)
            text = extractor.extract(content)
            is_scanned = len(text.strip()) < 50 if text else True
        except Exception as e:
            logger.error("pipeline_stage=extraction error=%s", str(e))
            return ParserResponse(
                status="error",
                error=f"Extraction failed: {str(e)}",
                meta={"filename": filename}
            )

        # ── Stage 2: Format Detection ───────────────────────────────
        fmt = self.detector.detect(text)
        bank = getattr(self.detector, "detect_bank", lambda x: "Unknown")(text)
        metadata = self.header_extractor.extract(text)
        metadata.bank_name = bank

        # ── SAFETY CHECK: Granular Bank Kill Switch ──────────────────
        if not safety_manager.is_bank_enabled(bank):
            logger.critical(f"Bank kill-switch active for {bank}. Blocking request.")
            return ParserResponse(
                status="error",
                reconciliation_score=0.0,
                transactions=[],
                error=f"Bank '{bank}' is temporarily disabled for maintenance.",
                meta={"bank": bank}
            )

        # ── Stage 3: Multi-Strategy Parsing (Parallel) ─────────────────
        responses = await self._run_parsing_parallel(content, text, fmt, bank, is_scanned, user_id=user_id, tier=tier)
        
        if not responses:
            return ParserResponse(
                status="error",
                reconciliation_score=0.0,
                transactions=[],
                error="No enabled parsers available for this request.",
                meta={"filename": filename, "bank": bank}
            )

        # ── Stage 4: Cross-Parser Reconciliation ──────────────────────
        result = self.reconciler.reconcile_multi(responses)
        result.statement_metadata = metadata
        parser_failures = [
            {
                "parser": response.meta.get("parser_name"),
                "error_code": response.meta.get("error_code"),
                "message": response.error,
            }
            for response in responses
            if response.status not in ("success", "no_transactions")
        ]
        if parser_failures:
            result.meta["parser_failures"] = parser_failures
        
        # ── Stage 4b: Fallback (DISABLED)
        # Cloud AI fallback removed ───────────────────────



        # ── Stage 5: Validation ───────────────────────────────────────
        try:
            validation = self.validator.validate(result.transactions)
            # ValidationResult has validations: list[TransactionValidation], NOT flags directly
            total_flags = []
            for v in validation.validations:
                total_flags.extend([f.value if hasattr(f, 'value') else str(f) for f in v.flags])
            result.meta["validation_flags"] = list(set(total_flags)) # All unique flags
            result.meta["confidence_score"] = min(result.reconciliation_score, validation.overall_score)
        except Exception as e:
            logger.warning("pipeline_stage=validation error=%s", str(e))
            validation = None

        # ── Stage 6: Categorization (now with Learning Hook) ──────────
        try:
            result.transactions = self.categorizer.annotate(result.transactions)
        except Exception as e:
            logger.warning("pipeline_stage=categorization error=%s", str(e))

        # ── Stage 7: SLA & Cost Tracking ──────────────────────────────
        processing_time = time.time() - start_time
        
        # Record end-to-end SLA
        sla_tracker.record_execution(processing_time, tier=tier, parser_name="pipeline")
        
        # Calculate and record total task cost (FIXED at 0.0 for deterministic local parsers)
        total_cost = 0.0
        # cost_guard.record_cost(user_id, total_cost)
        
        # Record bank-specific performance
        metrics.record_usage("pipeline", processing_time, success=True, cost=total_cost, bank=bank)

        result.meta.update({
            "pipeline_version":        "4.1.0-hardened",
            "format_type":             fmt.value if hasattr(fmt, 'value') else str(fmt),
            "bank":                    result.meta.get("bank", bank),
            "is_scanned":              is_scanned,
            "processing_time_seconds": round(processing_time, 3),
            "reconciliation_status":   result.status,
            "tier":                    tier,
            "total_task_cost":         round(total_cost, 6),
            "validation": {
                "overall_score":   getattr(validation, "overall_score", None),
                "invalid_count":   getattr(validation, "invalid_count", None),
            } if validation else {},
        })

        return result

    async def _run_parsing_parallel(self, content: bytes, text: str, fmt: Any, bank: str, is_scanned: bool, **kwargs: Any) -> list[ParserResponse]:
        """Execute top N enabled parsers in parallel and collect results."""
        user_id = kwargs.get("user_id", "anonymous")
        tier = kwargs.get("tier", "free")
        
        available_parsers = ParserRegistry.get_ranked_parsers(content, text, user_id=user_id, tier=tier, bank=bank)
        
        active_parsers = [
            p for p in available_parsers 
            if safety_manager.is_parser_enabled(p.name)
        ]
        
        if not active_parsers:
            return []

        top_parsers = active_parsers[: max(1, settings.parser_parallelism)]
        
        tasks = [
            self._execute_parser_safe(p, content, text, bank=bank, is_scanned=is_scanned, user_id=user_id, tier=tier)
            for p in top_parsers
        ]
        
        return await asyncio.gather(*tasks)

    async def _execute_parser_safe(self, parser: Any, content: bytes, text: str, **kwargs: Any) -> ParserResponse:
        """Execute a single parser with safety breakers, metrics, and SLA tracking."""
        start = time.time()
        user_id = kwargs.get("user_id", "anonymous")
        tier = kwargs.get("tier", "free")
        bank = kwargs.get("bank", "unknown")
        
        # ── CIRCUIT BREAKER: (DISABLED for local parsers)
        pass

        try:
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, functools.partial(parser.parse, content, text, **kwargs)),
                timeout=settings.parser_execution_timeout_seconds,
            )
            
            duration = time.time() - start
            
            # ── COST TRACKING: (DISABLED) ──
            cost = 0.0
            
            # Record per-parser metrics and individual parser SLA
            metrics.record_usage(parser.name, duration, success=(result.status == "success"), cost=cost, bank=bank)
            sla_tracker.record_execution(duration, tier=tier, parser_name=parser.name)
            
            result.meta.update({"parser_cost": cost, "parser_name": parser.name, "parser_version": parser.version})
            return result
        except asyncio.TimeoutError:
            duration = time.time() - start
            logger.error("Parser %s timed out after %.2fs", parser.name, settings.parser_execution_timeout_seconds)
            metrics.record_usage(parser.name, duration, success=False, bank=bank)
            return ParserResponse(
                status="error",
                error=f"Parser {parser.name} timed out after {settings.parser_execution_timeout_seconds:.1f}s",
                transactions=[],
                reconciliation_score=0.0,
                meta={
                    "parser_name": parser.name,
                    "parser_version": getattr(parser, "version", "unknown"),
                    "error_code": "PARSER_TIMEOUT",
                    "timeout_seconds": settings.parser_execution_timeout_seconds,
                },
            )
            
        except Exception as e:
            duration = time.time() - start
            logger.error(f"Parser {parser.name} failed: {str(e)}")
            # if breaker: breaker.record_failure()
            metrics.record_usage(parser.name, duration, success=False, bank=bank)
            return ParserResponse(
                status="error",
                error=str(e),
                transactions=[],
                reconciliation_score=0.0,
                meta={
                    "parser_name": parser.name,
                    "parser_version": getattr(parser, "version", "unknown"),
                    "error_code": "PARSER_EXECUTION_FAILED",
                },
            )
