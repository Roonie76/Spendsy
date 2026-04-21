"""
TORA Tiering Configuration - Defines feature access and model selection by tier.
Mirrors finance-service tier levels: free, pro, enterprise
"""

from enum import Enum
from typing import Dict, Any


class ToraUserTier(str, Enum):
    """User subscription tiers for TORA access."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TieringConfig:
    """Feature matrix for each tier."""

    # LLM Model Selection (Now routing to local Ollama models)
    MODEL_SELECTION: Dict[ToraUserTier, str] = {
        ToraUserTier.FREE: "tora",           # Gemma 4 E2B (7.2GB)
        ToraUserTier.PRO: "tora",            # TORA+ disabled — routes to TORA until fine-tuning
        ToraUserTier.ENTERPRISE: "tora"      # TORA+ disabled — routes to TORA until fine-tuning
    }

    # Autonomous Action Capability — all tiers can act autonomously (restrictions lifted)
    AUTONOMOUS_ACTIONS: Dict[ToraUserTier, bool] = {
        ToraUserTier.FREE: True,
        ToraUserTier.PRO: True,
        ToraUserTier.ENTERPRISE: True
    }

    # Conversation Memory — unlimited for every tier (0 == unlimited)
    CONVERSATION_MEMORY_LIMIT: Dict[ToraUserTier, int] = {
        ToraUserTier.FREE: 0,
        ToraUserTier.PRO: 0,
        ToraUserTier.ENTERPRISE: 0
    }

    # Simulation Complexity — full suite available to every tier
    _ALL_SIMULATIONS = [
        "basic_savings_rate",
        "loan_optimization",
        "tax_regime_comparison",
        "subscription_detection",
        "portfolio_optimization"
    ]
    SIMULATION_FEATURES: Dict[ToraUserTier, list] = {
        ToraUserTier.FREE: _ALL_SIMULATIONS,
        ToraUserTier.PRO: _ALL_SIMULATIONS,
        ToraUserTier.ENTERPRISE: _ALL_SIMULATIONS
    }

    # Data Sanitization — same permissive defaults for all tiers; account numbers still masked
    _SANITIZATION_DEFAULT = {
        "expose_bank_names": True,
        "expose_account_numbers": False,
        "expose_card_details": True,
        "expose_transaction_titles": True
    }
    DATA_SANITIZATION: Dict[ToraUserTier, dict] = {
        ToraUserTier.FREE: _SANITIZATION_DEFAULT,
        ToraUserTier.PRO: _SANITIZATION_DEFAULT,
        ToraUserTier.ENTERPRISE: _SANITIZATION_DEFAULT
    }

    # Tax Intelligence — all tax features available to every tier
    _ALL_TAX_FEATURES = [
        "regime_comparison",
        "profile_update_suggestions",
        "whatif_simulations",
        "investment_recommendations"
    ]
    TAX_FEATURES: Dict[ToraUserTier, list] = {
        ToraUserTier.FREE: _ALL_TAX_FEATURES,
        ToraUserTier.PRO: _ALL_TAX_FEATURES,
        ToraUserTier.ENTERPRISE: _ALL_TAX_FEATURES
    }

    # Audit/Analysis Frequency — hourly for all tiers
    AUDIT_FREQUENCY_HOURS: Dict[ToraUserTier, int] = {
        ToraUserTier.FREE: 1,
        ToraUserTier.PRO: 1,
        ToraUserTier.ENTERPRISE: 1
    }

    # Action Confirmation — only real-money transactions still require confirmation
    REQUIRES_CONFIRMATION: Dict[ToraUserTier, list] = {
        ToraUserTier.FREE: ["execute_transaction"],
        ToraUserTier.PRO: ["execute_transaction"],
        ToraUserTier.ENTERPRISE: ["execute_transaction"]
    }

    @classmethod
    def get_model_for_tier(cls, tier: str) -> str:
        """Get the LLM model name for a user tier."""
        try:
            tier_enum = ToraUserTier(tier.lower())
            return cls.MODEL_SELECTION.get(tier_enum, "tora")
        except (ValueError, AttributeError):
            return "tora"  # Default to free tier model

    @classmethod
    def can_act_autonomously(cls, tier: str) -> bool:
        """Check if tier allows autonomous actions."""
        return True

    @classmethod
    def get_memory_limit(cls, tier: str) -> int:
        """Get conversation memory turns for tier (0 == unlimited)."""
        return 0

    @classmethod
    def get_simulations(cls, tier: str) -> list:
        """Get available simulation features for tier."""
        return list(cls._ALL_SIMULATIONS)

    @classmethod
    def get_tax_features(cls, tier: str) -> list:
        """Get available tax features for tier."""
        return list(cls._ALL_TAX_FEATURES)

    @classmethod
    def should_expose_pii(cls, tier: str, pii_type: str) -> bool:
        """Check if tier should expose specific PII type."""
        return cls._SANITIZATION_DEFAULT.get(f"expose_{pii_type}", False)

    @classmethod
    def requires_action_confirmation(cls, tier: str, action: str) -> bool:
        """Check if action requires user confirmation for tier."""
        return action == "execute_transaction"
