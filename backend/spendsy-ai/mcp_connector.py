import logging
import os
import json
import asyncio
from typing import Dict, Any, Optional
from mcp import ClientSession
from mcp.client.sse import sse_client
from config import settings

logger = logging.getLogger(__name__)

class MCPConnector:
    """
    Client connector for TORA to interact with Spendsy MCP tools.
    Connects via SSE to the Spendsy MCP server.
    """
    
    def __init__(self, server_url: str = None):
        # Default to the internal Docker URL for spendsy-mcp
        self.server_url = server_url or os.getenv("SPENDSY_MCP_URL", "http://spendsy-mcp:8006/mcp/sse")
        self._session = None
        self._exit_stack = None

    async def _ensure_connection(self):
        """Lazy initialization of the MCP session."""
        if self._session is not None:
            return

        try:
            from contextlib import AsyncExitStack
            self._exit_stack = AsyncExitStack()
            
            logger.info(f"Connecting to MCP Server at {self.server_url}...")
            async def get_session():
                async with sse_client(self.server_url) as (read_stream, write_stream):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        return session

            # Note: For long-running agents, we would ideally keep this session open.
            # For now, we connect on-demand or use a persistent singleton.
            pass
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Invoke a tool on the MCP server."""
        try:
            async with sse_client(self.server_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    logger.info(f"Calling MCP tool: {tool_name} with args: {arguments}")
                    result = await session.call_tool(tool_name, arguments)
                    
                    # MCP content items are usually in a 'content' list
                    if hasattr(result, 'content') and result.content:
                        text_content = result.content[0].text
                        try:
                            return json.loads(text_content)
                        except json.JSONDecodeError:
                            return text_content
                    return result
        except Exception as e:
            logger.error(f"MCP tool call failed ({tool_name}): {e}")
            return {"error": str(e)}

# Singleton instance for easy access
mcp_connector = MCPConnector()

async def fetch_context_via_mcp(user_id: int) -> Dict[str, Any]:
    """Helper to fetch full financial context using the MCP tool."""
    result = await mcp_connector.call_tool("get_full_financial_context", {"user_id": user_id})
    if isinstance(result, dict) and "error" in result:
        logger.warning(f"MCP context fetch failed: {result['error']}")
        return {}
    return result
