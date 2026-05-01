import logging
import asyncio
from agents.tora.live_fetchers.browser_client import obscura_client

logger = logging.getLogger(__name__)

async def search_and_scrape(query: str):
    """
    Internal helper to search the internet and scrape the top result.
    """
    # Use Google Search as the entry point
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    
    # Selectors for Google Search results (titles and snippets)
    search_selectors = {
        "results": "div.g",
    }
    
    logger.info(f"Searching internet for: {query}")
    search_results = await obscura_client.scrape(search_url, search_selectors)
    
    if "error" in search_results:
        return f"Search failed: {search_results['error']}"
    
    # For a real implementation, we might want to pick a URL and scrape it.
    # For now, we'll return the search page content as a summary.
    return f"Search results for '{query}': {str(search_results)[:500]}..."

def search_internet(user_id: int, query: str):
    """
    Search the internet for real-time data (car prices, interest rates, etc.)
    and return a summary.
    """
    logger.info(f"TORA tool triggered: search_internet for user {user_id}, query={query}")
    
    try:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        result = loop.run_until_complete(search_and_scrape(query))
        return result
    except Exception as e:
        logger.error(f"Error in search_internet tool: {e}")
        return f"Error searching internet: {str(e)}"
