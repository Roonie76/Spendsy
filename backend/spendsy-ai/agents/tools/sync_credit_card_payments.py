import logging
import asyncio
from mcp_connector import mcp_connector

logger = logging.getLogger(__name__)

def sync_credit_card_payments(user_id: int, params: dict = None):
    """
    Sync tool wrapper for TORA.
    This calls the MCP tool asynchronously.
    """
    logger.info(f"TORA tool triggered: sync_credit_card_payments for user {user_id}")
    
    # Since the agent's tool execution loop in tora_agent.py is currently sync (calling registry[name](user_id, params)),
    # we use a helper to run the async MCP call.
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    result = loop.run_until_complete(
        mcp_connector.call_tool("sync_credit_card_payments", {"user_id": user_id})
    )
    return result
