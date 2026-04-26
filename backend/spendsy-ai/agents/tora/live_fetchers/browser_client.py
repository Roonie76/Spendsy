import logging
import asyncio
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright
from config import settings

logger = logging.getLogger(__name__)

class ObscuraClient:
    """
    Client for Obscura (Headless Rust Browser) via CDP.
    Uses Playwright to connect to a remote CDP endpoint.
    """
    
    def __init__(self, cdp_url: str = None):
        # Default to the URL specified in the spec: ws://obscura:9222
        # On local dev it might be localhost:9222
        self.cdp_url = cdp_url or getattr(settings, "obscura_cdp_url", "ws://obscura:9222")

    async def scrape(self, url: str, selectors: Dict[str, str], timeout: int = 800) -> Dict[str, Any]:
        """
        Connect to Obscura, navigate to URL, and extract data using selectors.
        """
        results = {}
        try:
            async with async_playwright() as p:
                logger.info(f"Connecting to Obscura at {self.cdp_url}")
                browser = await p.chromium.connect_over_cdp(self.cdp_url)
                context = await browser.new_context()
                page = await context.new_page()
                
                logger.info(f"Navigating to {url}")
                # Use a strict timeout as per spec (800ms total budget)
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                except Exception as e:
                    logger.warning(f"Navigation to {url} timed out or failed: {e}")
                    # Continue anyway, we might have partial data or want to try selectors
                
                for key, selector in selectors.items():
                    try:
                        element = await page.query_selector(selector)
                        if element:
                            results[key] = await element.inner_text()
                        else:
                            results[key] = None
                    except Exception as selector_err:
                        logger.debug(f"Selector {key} failed: {selector_err}")
                        results[key] = None
                
                await browser.close()
                
        except Exception as e:
            logger.error(f"Obscura scrape failed for {url}: {e}")
            return {"error": str(e)}
            
        return results

# Singleton instance
obscura_client = ObscuraClient()
