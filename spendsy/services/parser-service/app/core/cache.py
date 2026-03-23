import hashlib
import logging
from typing import Dict, Any, Optional
from app.core.schemas import ParserResponse
from app.core.registry import ParserRegistry

logger = logging.getLogger(__name__)

class ResultCache:
    """
    Content-hash based cache to avoid redundant parsing of identical files.
    Keys are a combination of file content hash and current active parser versions.
    Implemented with confidence-based reuse checks for production hardening.
    """
    _instance = None
    _cache: Dict[str, ParserResponse] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ResultCache, cls).__new__(cls)
        return cls._instance

    def _get_cache_key(self, content: bytes) -> str:
        # 1. Content Hash
        content_hash = hashlib.sha256(content).hexdigest()
        
        # 2. Version Hash (to invalidate cache if any parser version changes)
        v_string = "|".join([
            f"{name}:{ver}" 
            for name, ver in sorted(ParserRegistry._active_versions.items())
        ])
        version_hash = hashlib.md5(v_string.encode()).hexdigest()
        
        return f"{content_hash}_{version_hash}"

    def get(self, content: bytes) -> Optional[ParserResponse]:
        key = self._get_cache_key(content)
        result = self._cache.get(key)
        
        if result:
            # ── CONFIDENCE CHECK ──────────────────────────────────
            # If the cached result has a very low reconciliation score, 
            # we consider it a miss to allow better parsers a chance.
            if result.reconciliation_score < 0.5:
                logger.info(f"Cache SKIP: Low confidence (score={result.reconciliation_score})")
                return None
                
            logger.info(f"Cache HIT for content hash {key[:16]}")
            result.meta["cache_hit"] = True
            return result
        return None

    def set(self, content: bytes, result: ParserResponse):
        # Don't cache error responses
        if result.status != "success":
            return
            
        key = self._get_cache_key(content)
        self._cache[key] = result
        logger.debug(f"Cache SET for content hash {key[:16]}")

    def clear(self):
        self._cache.clear()

# Global instance
result_cache = ResultCache()
