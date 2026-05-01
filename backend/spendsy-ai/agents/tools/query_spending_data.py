import logging
import asyncio
from mcp_connector import mcp_connector

logger = logging.getLogger(__name__)

def query_spending_data(user_id: int, query_type: str):
    """
    Run a predefined safe query on spending data.
    Supported types: 'monthly_category_totals', 'merchant_statistics', 'income_expense_ratio'
    """
    logger.info(f"TORA tool triggered: query_spending_data for user {user_id}, type={query_type}")
    
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        result = loop.run_until_complete(
            mcp_connector.call_tool("query_spending_data", {"user_id": user_id, "query_type": query_type})
        )
        return result
    except Exception as e:
        logger.error(f"Error in query_spending_data tool: {e}")
        return f"Error querying spending data: {str(e)}"
