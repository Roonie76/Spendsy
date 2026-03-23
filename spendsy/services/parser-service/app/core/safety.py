import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)

class SafetyManager:
    """
    Centralized control for system safety (kill switches) and feature flags.
    Supports global, parser-level, and per-bank/service disabling.
    """
    _instance = None
    _global_enabled: bool = True
    _parser_flags: Dict[str, bool] = {
        "llm": True,
        "cloud": True,
        "regex": True,
        "tabular": True,
    }
    _disabled_banks: Set[str] = set()
    _disabled_services: Set[str] = set()
    _experimental_features: Set[str] = set()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SafetyManager, cls).__new__(cls)
        return cls._instance

    def is_system_enabled(self) -> bool:
        return self._global_enabled

    def disable_system(self):
        self._global_enabled = False
        logger.critical("SYSTEM KILL SWITCH ACTIVATED: Global processing disabled.")

    def enable_system(self):
        self._global_enabled = True
        logger.info("System processing re-enabled.")

    def is_parser_enabled(self, parser_name: str) -> bool:
        return self._parser_flags.get(parser_name.lower(), True)

    def set_parser_flag(self, parser_name: str, enabled: bool):
        self._parser_flags[parser_name.lower()] = enabled

    def disable_bank(self, bank_name: str):
        self._disabled_banks.add(bank_name.lower())
        logger.warning(f"BANK KILL SWITCH: Disabled processing for {bank_name}")

    def is_bank_enabled(self, bank_name: str) -> bool:
        return bank_name.lower() not in self._disabled_banks

    def disable_service(self, service_name: str):
        self._disabled_services.add(service_name.lower())
        logger.warning(f"SERVICE KILL SWITCH: Internal dependency {service_name} marked as DISABLED")

    def is_service_enabled(self, service_name: str) -> bool:
        return service_name.lower() not in self._disabled_services

    def enable_feature(self, feature_name: str):
        self._experimental_features.add(feature_name)

    def is_feature_enabled(self, feature_name: str) -> bool:
        return feature_name in self._experimental_features

# Global instance
safety_manager = SafetyManager()
