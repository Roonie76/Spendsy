from __future__ import annotations

import logging
from typing import Dict, Type, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.base_parser import BaseParser
    from app.core.format_detector import BankStatementFormat

logger = logging.getLogger(__name__)

class ParserRegistry:
    """
    Registry for all bank statement parsers.
    Supports multi-versioning, active version switching, rollbacks, and SLA auto-mitigation.
    """
    _parsers: Dict[str, Dict[str, Type[BaseParser]]] = {}
    _active_versions: Dict[str, str] = {}

    @classmethod
    def register(cls, format_name: str, parser_class: Type[BaseParser]):
        version = "1.0.0"
        try:
            temp_instance = parser_class()
            version = temp_instance.version
        except Exception: pass

        if format_name not in cls._parsers:
            cls._parsers[format_name] = {}
        
        cls._parsers[format_name][version] = parser_class
        if format_name not in cls._active_versions:
            cls._active_versions[format_name] = version
        logger.info(f"Registered parser: {format_name} V{version}")

    @classmethod
    def set_active_version(cls, format_name: str, version: str):
        if format_name in cls._parsers and version in cls._parsers[format_name]:
            cls._active_versions[format_name] = version
            logger.info(f"Activated version {version} for {format_name}")

    @classmethod
    def rollback_version(cls, format_name: str):
        if format_name not in cls._parsers: return
        versions = sorted(cls._parsers[format_name].keys())
        if len(versions) < 2: return
        current = cls._active_versions.get(format_name)
        try:
            idx = versions.index(current)
            if idx > 0: cls.set_active_version(format_name, versions[idx - 1])
        except ValueError:
            cls.set_active_version(format_name, versions[-2])

    @classmethod
    def get_parser(cls, format_name: str, version: str | None = None) -> BaseParser | None:
        v = version or cls._active_versions.get(format_name)
        parser_class = cls._parsers.get(format_name, {}).get(v)
        return parser_class() if parser_class else None

    @classmethod
    def get_ranked_parsers(cls, content: bytes, text: str, user_id: str = "anonymous", **kwargs: Any) -> list[BaseParser]:
        """
        Rank the ACTIVE version of all registered parsers by their can_handle() score.
        Now includes SLA auto-mitigation and Cost Guardrails.
        """
        results = []
        tier = kwargs.get("tier", "free")
        from app.core.observability import sla_tracker, cost_guard
        
        # 1. COST GUARD: Stop expensive strategies if budget hit
        is_budget_ok = cost_guard.is_within_budget(user_id, tier)

        for name in cls._parsers.keys():
            # Skip expensive parsers if policy dictates
            is_expensive = any(kw in name.lower() for kw in ["llm", "cloud"])
            if is_expensive and not is_budget_ok:
                logger.info(f"CostGuard: skipping expensive parser={name} for user={user_id}")
                continue

            try:
                parser = cls.get_parser(name)
                if not parser: continue
                    
                score = parser.can_handle(content, text, **kwargs)
                if score > 0:
                    # 2. SLA AUTO-MITIGATION: Apply penalty to slow parsers
                    # Penalty increases every 5 SLA violations
                    violations = sla_tracker.get_violation_count(name)
                    sla_penalty = (violations // 5) * 10 
                    
                    results.append({
                        "name": name,
                        "score": score,
                        "priority": parser.priority + sla_penalty,
                        "instance": parser
                    })
            except Exception as e:
                logger.warning(f"Error scoring parser {name}: {e}")
                continue
        
        # Sort by score (descending), then priority (ascending / lower value first)
        results.sort(key=lambda x: (x["score"], -x["priority"]), reverse=True)
        return [r["instance"] for r in results]

def initialize_registry():
    from app.parsers.type_a_parser import TypeAParser
    from app.parsers.type_b_parser import TypeBParser
    from app.parsers.type_c_parser import TypeCParser
    from app.parsers.tabular_parser import TabularParser
    from app.parsers.llm_parser import LLMParser
    from app.parsers.cloud_parser import CloudParser
    from app.parsers.citibank_parser import CitibankParser
    from app.core.regex_parser import RegexParser

    ParserRegistry.register("TYPE_A", TypeAParser)
    ParserRegistry.register("TYPE_B", TypeBParser)
    ParserRegistry.register("TYPE_C", TypeCParser)
    ParserRegistry.register("tabular", TabularParser)
    ParserRegistry.register("llm", LLMParser)
    ParserRegistry.register("cloud", CloudParser)
    ParserRegistry.register("citibank", CitibankParser)
    ParserRegistry.register("regex", RegexParser)
