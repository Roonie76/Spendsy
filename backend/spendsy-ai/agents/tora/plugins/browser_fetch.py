import logging
import yaml
import os
from typing import Dict, Any, List, Optional
from ..live_fetchers.browser_client import obscura_client
from ..fetch_registry import FetchStrategy, FetchResult, FetchPlugin, fact

# PLUGIN_ID used for registration
PLUGIN_ID = "browser"

def fallback_browser(entity: str, context: Dict[str, Any] = None) -> FetchResult:
    """Zero-latency fallback for browser queries."""
    return FetchResult(
        facts={
            "status": fact("Checking live prices...", "system"),
            "notice": fact("Obtaining real-time data from web sources.", "browser_plugin")
        },
        provenance={"plugin_id": PLUGIN_ID, "any_fallback_used": True}
    )

async def fetch_browser_data(entity: str, context: Dict[str, Any] = None) -> FetchResult:
    """
    TORA plugin to fetch live data from the web using Obscura.
    Matches flights, hotels, electronic prices, etc.
    """
    logger.info(f"Obscura browser fetch triggered for entity: {entity}")
    
    # Simple mapping for demonstration
    target_url = ""
    selectors = {}
    
    if "flight" in entity.lower():
        target_url = "https://www.google.com/search?q=flights+to+goa"
        selectors = {"price": ".pS7G2b"}
    elif "hotel" in entity.lower():
        target_url = "https://www.booking.com/searchresults.en-gb.html?ss=Goa"
        selectors = {"price": "[data-testid='price-and-discounted-price']"}
    
    if not target_url:
        return await fallback_browser(entity, context)

    # Perform the scrape
    from tracer import HAS_LIGHTNING, tracer as lightning_tracer
    if HAS_LIGHTNING and lightning_tracer:
        with lightning_tracer.trace(agent_id="tora.context.browser", input={"url": target_url}) as span:
            scraped_data = await obscura_client.scrape(target_url, selectors)
            span.set_output(scraped_data)
    else:
        scraped_data = await obscura_client.scrape(target_url, selectors)
    
    if "error" in scraped_data:
        return await fallback_browser(entity, context)

    facts = {k: fact(v, "live_scrape") for k, v in scraped_data.items()}
    return FetchResult(
        facts=facts,
        provenance={"plugin_id": PLUGIN_ID, "any_fallback_used": False}
    )

PLUGIN = FetchPlugin(
    plugin_id=PLUGIN_ID,
    entity_keys=["flight", "hotel", "booking", "price check", "compare prices", "amazon", "flipkart", "makemytrip", "fd rate", "insurance quote"],
    fetch_profile=["browser"],
    token_budget=300,
    fetcher=fetch_browser_data,
    fallback=fallback_browser,
    strategy=FetchStrategy.LIVE_SCRAPE,
    critical_freshness=True
)
