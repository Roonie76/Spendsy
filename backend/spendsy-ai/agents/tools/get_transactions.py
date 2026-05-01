import logging
import asyncio
from mcp_connector import mcp_connector

logger = logging.getLogger(__name__)

def get_transactions(user_id: int, limit: int = 50):
    """
    Fetch the latest transactions for a user.
    """
    logger.info(f"TORA tool triggered: get_transactions for user {user_id}, limit={limit}")
    
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        result = loop.run_until_complete(
            mcp_connector.call_tool("get_transactions", {"user_id": user_id, "limit": limit})
        )
        return result
    except Exception as e:
        logger.error(f"Error in get_transactions tool: {e}")
        return f"Error fetching transactions: {str(e)}"
