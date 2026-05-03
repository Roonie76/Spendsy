import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, Tuple

from mcp import ClientSession
from mcp.client.sse import sse_client

from config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tiny in-process TTL cache for MCP responses.
#
# Rationale: the MCP "get_full_financial_context" tool returns the user's
# full balance / txn / goals / loans snapshot. That snapshot changes when
# the user ingests a statement or edits a transaction — not on every chat
# turn. A short TTL (default 45s) means follow-up questions in the same
# conversation reuse the snapshot and skip a fresh SSE handshake.
#
# Invalidation paths:
#   - TTL expiry (automatic)
#   - `invalidate_user_cache(user_id)` — call from write endpoints when
#     transactions/loans/goals change, so the next turn sees fresh data.
#
# This is intentionally process-local. Multi-worker deployments will have
# per-worker caches, which is fine — the cost of occasional staleness is
# much lower than the current cost of re-handshaking every turn.
# ---------------------------------------------------------------------------

_DEFAULT_TTL_SECONDS = int(os.getenv("MCP_CACHE_TTL_SECONDS", "45"))
_cache: Dict[Tuple[str, Tuple[Tuple[str, Any], ...]], Tuple[float, Any]] = {}
_cache_lock = asyncio.Lock()


def _cache_key(tool_name: str, arguments: Dict[str, Any]) -> Tuple[str, Tuple[Tuple[str, Any], ...]]:
    """Produce a hashable key from (tool_name, sorted kwargs)."""
    # JSON-stringify unhashable values so we can still key on them.
    norm: Dict[str, Any] = {}
    for k, v in arguments.items():
        try:
            hash(v)
            norm[k] = v
        except TypeError:
            norm[k] = json.dumps(v, sort_keys=True, default=str)
    return tool_name, tuple(sorted(norm.items()))


def invalidate_user_cache(user_id: int) -> None:
    """Drop any cached MCP responses for a given user.

    Call this from write endpoints whenever finance data changes:
        - transaction create/edit/delete
        - loan create/payment
        - goal contribution / plan update
        - credit card statement ingest
    Safe to call even if no entry exists.
    """
    to_drop = [
        key for key in _cache
        if any(k == "user_id" and v == user_id for k, v in key[1])
    ]
    for key in to_drop:
        _cache.pop(key, None)
    if to_drop:
        logger.info("Invalidated %d MCP cache entries for user %s", len(to_drop), user_id)


def clear_cache() -> None:
    """Drop every cached entry. Primarily for tests."""
    _cache.clear()


class MCPConnector:
    """Client connector for TORA to interact with Spendsy MCP tools.

    Each `call_tool` opens a fresh SSE session. That's intentional for now —
    the `mcp` client's session objects aren't trivially long-lived across
    async contexts, and the cache layer above removes most of the perf cost
    by reusing responses within a 45s window.
    """

    def __init__(self, server_url: str | None = None):
        self.server_url = server_url or os.getenv(
            "SPENDSY_MCP_URL", "http://spendsy-mcp:8006/mcp/sse"
        )

    async def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        *,
        use_cache: bool = True,
        ttl: int | None = None,
    ) -> Any:
        """Invoke a tool on the MCP server.

        Args:
            tool_name: MCP tool identifier.
            arguments: kwargs for the tool.
            use_cache: if True (default), honors the process-local TTL cache.
                Callers that need strictly-fresh data (e.g. post-write reads)
                should pass False.
            ttl: per-call TTL override in seconds. None → default.
        """
        key = _cache_key(tool_name, arguments)
        effective_ttl = ttl if ttl is not None else _DEFAULT_TTL_SECONDS

        if use_cache and effective_ttl > 0:
            async with _cache_lock:
                entry = _cache.get(key)
                if entry:
                    expires_at, cached_value = entry
                    if expires_at > time.time():
                        logger.debug("MCP cache hit for %s(%s)", tool_name, arguments)
                        return cached_value
                    _cache.pop(key, None)

        try:
            async with sse_client(self.server_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    logger.info(f"Calling MCP tool: {tool_name} with args: {arguments}")
                    result = await session.call_tool(tool_name, arguments)

                    if hasattr(result, "content") and result.content:
                        text_content = result.content[0].text
                        try:
                            value = json.loads(text_content)
                        except json.JSONDecodeError:
                            value = text_content
                    else:
                        value = result
        except Exception as e:
            logger.error(f"MCP tool call failed ({tool_name}): {e}")
            return {"error": str(e)}

        # Only cache successful responses — never cache error payloads.
        if use_cache and effective_ttl > 0 and not (isinstance(value, dict) and "error" in value):
            async with _cache_lock:
                _cache[key] = (time.time() + effective_ttl, value)

        return value


# Singleton instance for easy access
mcp_connector = MCPConnector()


async def fetch_context_via_mcp(user_id: int, *, use_cache: bool = True) -> Dict[str, Any]:
    """Helper to fetch full financial context using the MCP tool."""
    result = await mcp_connector.call_tool(
        "get_full_financial_context",
        {"user_id": user_id},
        use_cache=use_cache,
    )
    if isinstance(result, dict) and "error" in result:
        logger.warning(f"MCP context fetch failed: {result['error']}")
        return {}
    if isinstance(result, str):
        # Result should have been a dict. If it's a string, it's likely an unparsed error message.
        return {"error": result}
    return result
