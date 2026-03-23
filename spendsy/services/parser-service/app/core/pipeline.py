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
from app.core.observability import metrics, sla_tracker, cost_tracker, cost_guard, llm_breaker, cloud_breaker
from app.core.safety import safety_manager

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
        
        # ── Stage 4b: Cloud AI Fallback ───────────────────────────────
        if not result.transactions or result.reconciliation_score < 0.2:
            reason = "0 transactions" if not result.transactions else f"low confidence (score={result.reconciliation_score})"
            logger.info(f"Primary parsers yielded {reason}. Triggering cloud AI fallback as last resort...")
            cloud_parser = ParserRegistry.get_parser("cloud")
            if cloud_parser and safety_manager.is_parser_enabled("cloud"):
                fallback_res = await self._execute_parser_safe(cloud_parser, content, text, bank=bank, is_scanned=is_scanned, user_id=user_id, tier=tier)
                if fallback_res and fallback_res.transactions:
                    # Only override if the fallback actually found something
                    logger.info(f"Cloud AI fallback successful, extracted {len(fallback_res.transactions)} transactions.")
                    result = fallback_res



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
        
        # Calculate and record total task cost
        total_cost = sum([r.meta.get("parser_cost", 0.0) for r in responses])
        cost_guard.record_cost(user_id, total_cost)
        
        # Record bank-specific performance
        metrics.record_usage("pipeline", processing_time, success=True, cost=total_cost, bank=bank)

        result.meta.update({
            "pipeline_version":        "4.1.0-hardened",
            "format_type":             str(fmt),
            "bank":                    bank,
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

        top_parsers = active_parsers[:2]
        
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
        
        # ── CIRCUIT BREAKER: Check if external dependency is healthy ─
        breaker = None
        if "llm" in parser.name.lower(): breaker = llm_breaker
        elif "cloud" in parser.name.lower(): breaker = cloud_breaker
            
        if breaker and not breaker.can_execute():
            return ParserResponse(status="skipped", transactions=[], reconciliation_score=0.0, meta={"reason": "circuit_breaker_open"})

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, functools.partial(parser.parse, content, text, **kwargs))
            
            duration = time.time() - start
            
            # ── COST TRACKING ──
            cost = 0.0
            if "llm" in parser.name.lower():
                cost = cost_tracker.estimate_llm_cost(result.meta.get("input_tokens", 800), result.meta.get("output_tokens", 400))
            elif "ocr" in parser.name.lower():
                cost = cost_tracker.estimate_ocr_cost(pages=1)
            
            if breaker: breaker.record_success()
            
            # Record per-parser metrics and individual parser SLA
            metrics.record_usage(parser.name, duration, success=(result.status == "success"), cost=cost, bank=bank)
            sla_tracker.record_execution(duration, tier=tier, parser_name=parser.name)
            
            result.meta.update({"parser_cost": cost, "parser_name": parser.name, "parser_version": parser.version})
            return result
            
        except Exception as e:
            duration = time.time() - start
            logger.error(f"Parser {parser.name} failed: {str(e)}")
            if breaker: breaker.record_failure()
            metrics.record_usage(parser.name, duration, success=False, bank=bank)
            return ParserResponse(status="error", error=str(e), transactions=[], reconciliation_score=0.0)
