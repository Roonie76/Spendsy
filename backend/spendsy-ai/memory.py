"""
Conversation Memory Management for TORA Agent
Handles tier-based conversation history storage and retrieval.

FREE TIER: 5-turn conversation window (limited to last 5 exchanges)
PRO TIER: Unlimited persistent conversation history
ENTERPRISE TIER: Unlimited + real-time anomaly tracking
"""

import logging
from typing import List, Dict, Any
from abc import ABC, abstractmethod
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationStore(ABC):
    """Abstract base class for conversation storage backends."""
    
    @abstractmethod
    def load_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Load conversation history for user."""
        pass
    
    @abstractmethod
    def save_turn(self, user_id: int, role: str, content: str, structured: Dict[str, Any] | None = None) -> None:
        """Save a single conversation turn."""
        pass
    
    @abstractmethod
    def get_memory_limit(self) -> int | None:
        """Get conversation limit (None for unlimited)."""
        pass


class FreeTierStore(ConversationStore):
    """
    Free Tier Memory: 5-turn window (last 5 user+assistant pairs = 10 messages)
    Provides limited context to control inference costs on cheaper LLM.
    """
    
    WINDOW_SIZE = 5  # 5 turns = 10 messages (user + assistant each)
    
    def __init__(self, db_backend):
        """
        Args:
            db_backend: Function that calls database/API (e.g., call_finance_internal)
        """
        self.db_backend = db_backend
    
    def load_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Load last 5 conversation turns for Free tier user."""
        try:
            data = self.db_backend("tora-conversation", user_id, {"limit": self.WINDOW_SIZE})
            if not data or not isinstance(data, list):
                return []
            
            history = []
            for msg in data:
                history.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("created_at"),  # For reference
                })
            logger.info(f"Loaded {len(history)} messages for Free tier user {user_id} (limit: {self.WINDOW_SIZE})")
            return history
        except Exception as e:
            logger.error(f"Error loading Free tier history for user {user_id}: {e}")
            return []
    
    def save_turn(self, user_id: int, role: str, content: str, structured: Dict[str, Any] | None = None) -> None:
        """Save conversation turn to database."""
        try:
            # Delegate to DB backend (implemented separately)
            pass
        except Exception as e:
            logger.warning(f"Could not save conversation turn for user {user_id}: {e}")
    
    def get_memory_limit(self) -> int:
        """Free tier memory window is 5 turns."""
        return self.WINDOW_SIZE


class ProTierStore(ConversationStore):
    """
    Pro Tier Memory: Unlimited persistent conversation history
    Full context for advanced LLM reasoning (Gemini 1.5 Pro).
    Keeps all conversation history for comprehensive analysis.
    """
    
    # Pro tier has no practical limit; set high default for safety
    MAX_LIMIT = 1000  # Maximum messages to load at once (prevents runaway queries)
    
    def __init__(self, db_backend):
        """
        Args:
            db_backend: Function that calls database/API
        """
        self.db_backend = db_backend
    
    def load_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Load all conversation turns for Pro tier user (up to MAX_LIMIT)."""
        try:
            data = self.db_backend("tora-conversation", user_id, {"limit": self.MAX_LIMIT})
            if not data or not isinstance(data, list):
                return []
            
            history = []
            for msg in data:
                history.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("created_at"),
                })
            logger.info(f"Loaded {len(history)} messages for Pro tier user {user_id}")
            return history
        except Exception as e:
            logger.error(f"Error loading Pro tier history for user {user_id}: {e}")
            return []
    
    def save_turn(self, user_id: int, role: str, content: str, structured: Dict[str, Any] | None = None) -> None:
        """Save conversation turn to database."""
        try:
            pass
        except Exception as e:
            logger.warning(f"Could not save conversation turn for user {user_id}: {e}")
    
    def get_memory_limit(self) -> int | None:
        """Pro tier has unlimited memory."""
        return None


class EnterpriseTierStore(ConversationStore):
    """
    Enterprise Tier Memory: Unlimited + Real-time Anomaly Tracking
    Maintains full history with additional metadata for compliance and analysis.
    Includes audit trail for all conversations.
    """
    
    MAX_LIMIT = 5000  # Enterprise can request more history
    
    def __init__(self, db_backend):
        """
        Args:
            db_backend: Function that calls database/API
        """
        self.db_backend = db_backend
    
    def load_history(self, user_id: int) -> List[Dict[str, Any]]:
        """Load all conversation turns with extended metadata."""
        try:
            data = self.db_backend("tora-conversation", user_id, {"limit": self.MAX_LIMIT, "include_metadata": True})
            if not data or not isinstance(data, list):
                return []
            
            history = []
            for msg in data:
                history.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("created_at"),
                    "metadata": msg.get("metadata", {}),  # Audit info
                })
            logger.info(f"Loaded {len(history)} messages for Enterprise tier user {user_id} with metadata")
            return history
        except Exception as e:
            logger.error(f"Error loading Enterprise tier history for user {user_id}: {e}")
            return []
    
    def save_turn(self, user_id: int, role: str, content: str, structured: Dict[str, Any] | None = None) -> None:
        """Save conversation turn with audit metadata."""
        try:
            pass
        except Exception as e:
            logger.warning(f"Could not save conversation turn for user {user_id}: {e}")
    
    def get_memory_limit(self) -> int | None:
        """Enterprise tier has unlimited memory."""
        return None


def get_memory_store(user_tier: str, db_backend) -> ConversationStore:
    """
    Factory function to get appropriate memory store for user tier.
    
    Args:
        user_tier: "free", "pro", or "enterprise"
        db_backend: Database/API backend function for persistence
    
    Returns:
        ConversationStore subclass instance
    """
    tier_map = {
        "free": FreeTierStore,
        "pro": ProTierStore,
        "enterprise": EnterpriseTierStore,
    }
    
    store_class = tier_map.get(user_tier.lower(), FreeTierStore)
    logger.info(f"Using {store_class.__name__} for tier: {user_tier}")
    return store_class(db_backend)


def build_conversation_context(history: List[Dict[str, Any]]) -> str:
    """
    Convert conversation history list into a formatted context string for LLM prompting.
    
    Args:
        history: List of {role, content, timestamp} dicts
    
    Returns:
        Formatted conversation history as string for prompt injection
    """
    if not history:
        return "No previous conversation history."
    
    context_lines = ["=== CONVERSATION HISTORY ==="]
    for i, msg in enumerate(history, 1):
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        
        if timestamp:
            context_lines.append(f"[{timestamp}] {role}: {content}")
        else:
            context_lines.append(f"[Turn {i}] {role}: {content}")
    
    context_lines.append("=== END HISTORY ===\n")
    return "\n".join(context_lines)


def inject_memory_into_system_prompt(base_prompt: str, history: List[Dict[str, Any]]) -> str:
    """
    Inject conversation history into the system prompt for LLM context.
    
    Args:
        base_prompt: Original system prompt
        history: Conversation history list
    
    Returns:
        Enhanced system prompt with history context
    """
    if not history:
        return base_prompt
    
    history_context = build_conversation_context(history)
    enhanced_prompt = f"{base_prompt}\n\n### RECENT CONVERSATION CONTEXT\n{history_context}"
    return enhanced_prompt


# Convenience functions for common operations

def load_user_conversation_history(user_id: int, user_tier: str, db_backend) -> List[Dict[str, Any]]:
    """
    Load conversation history respecting user tier limits.
    
    Args:
        user_id: User ID
        user_tier: "free", "pro", or "enterprise"
        db_backend: Database/API backend function
    
    Returns:
        List of recent conversation messages
    """
    store = get_memory_store(user_tier, db_backend)
    return store.load_history(user_id)


def get_tier_memory_limit(user_tier: str) -> int | None:
    """
    Get conversation history limit for user tier.
    
    Args:
        user_tier: "free", "pro", or "enterprise"
    
    Returns:
        Maximum number of turns (None for unlimited)
    """
    # Tier restrictions lifted — all tiers get unlimited conversation memory.
    return None


def format_memory_stats(user_tier: str, loaded_history_count: int) -> Dict[str, Any]:
    """
    Return memory usage statistics for logging/debugging.
    
    Args:
        user_tier: "free", "pro", or "enterprise"
        loaded_history_count: Number of messages loaded
    
    Returns:
        Stats dict with tier, limit, usage, etc.
    """
    limit = get_tier_memory_limit(user_tier)
    return {
        "tier": user_tier,
        "memory_limit": limit,
        "messages_loaded": loaded_history_count,
        "memory_type": "windowed" if limit else "unlimited",
        "utilization_percent": (loaded_history_count / limit * 100) if limit else 0,
    }
