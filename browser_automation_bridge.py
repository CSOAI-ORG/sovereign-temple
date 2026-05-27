#!/usr/bin/env python3
"""
Browser Automation Bridge - Web Automation for SOV3
Enables AI to: search web, navigate pages, fill forms, extract data
Uses Playwright for robust browser automation
"""

import asyncio
import json
import os
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

log = logging.getLogger("browser-automation")


@dataclass
class BrowserConfig:
    headless: bool = True
    timeout: int = 30000
    viewport_width: int = 1280
    viewport_height: int = 720


class BrowserAutomationBridge:
    """
    Browser automation with Playwright
    - Web search and navigation
    - Form filling
    - Data extraction
    - Screenshot capture
    """

    def __init__(self, config: BrowserConfig = None):
        self.config = config or BrowserConfig()
        self.browser = None
        self.context = None
        self.page = None
        self._playwright = None

    async def initialize(self) -> bool:
        """Initialize browser"""
        try:
            from playwright.async_api import async_playwright

            self._playwright = async_playwright()
            await self._playwright.start()

            self.browser = await self._playwright.chromium.launch(
                headless=self.config.headless
            )

            self.context = await self.browser.new_context(
                viewport={
                    "width": self.config.viewport_width,
                    "height": self.config.viewport_height,
                }
            )

            self.page = await self.context.new_page()
            log.info("✅ Browser automation initialized")
            return True

        except ImportError:
            log.warning(
                "Playwright not installed: pip install playwright && playwright install chromium"
            )
            return False
        except Exception as e:
            log.error(f"Browser init failed: {e}")
            return False

    async def close(self):
        """Close browser"""
        if self.browser:
            await self.browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def search(self, query: str, num_results: int = 5) -> Dict:
        """Search the web and return results"""
        try:
            # Navigate to search engine
            await self.page.goto(
                "https://www.google.com/search?q=" + query.replace(" ", "+"),
                timeout=self.config.timeout,
            )

            # Wait for results
            await self.page.wait_for_selector("div.g", timeout=10000)

            results = []
            # Get search result elements
            for i, elem in enumerate(
                await self.page.query_selector_all("div.g")[:num_results]
            ):
                try:
                    title_elem = await elem.query_selector("h3")
                    title = await title_elem.inner_text() if title_elem else ""

                    link_elem = await elem.query_selector("a")
                    href = await link_elem.get_attribute("href") if link_elem else ""

                    snippet_elem = await elem.query_selector("div.VwiC3b")
                    snippet = await snippet_elem.inner_text() if snippet_elem else ""

                    results.append(
                        {
                            "title": title[:200],
                            "url": href[:300],
                            "snippet": snippet[:300],
                        }
                    )
                except:
                    continue

            return {"results": results, "query": query, "count": len(results)}

        except Exception as e:
            return {"error": str(e), "query": query}

    async def fetch_page(self, url: str, max_chars: int = 5000) -> Dict:
        """Fetch a page and extract content"""
        try:
            await self.page.goto(url, timeout=self.config.timeout)

            # Get page title
            title = await self.page.title()

            # Get main content (simplified)
            content = await self.page.content()

            # Extract readable text (basic)
            body = await self.page.query_selector("body")
            text = await body.inner_text() if body else ""

            return {
                "url": url,
                "title": title,
                "content": text[:max_chars],
                "length": len(text),
            }

        except Exception as e:
            return {"error": str(e), "url": url}

    async def fill_form(
        self, selectors: Dict[str, str], values: Dict[str, str]
    ) -> Dict:
        """Fill form fields"""
        try:
            for field, value in values.items():
                selector = selectors.get(field, field)
                await self.page.fill(selector, value)

            return {"success": True, "filled": list(values.keys())}
        except Exception as e:
            return {"error": str(e)}

    async def click_element(self, selector: str) -> Dict:
        """Click an element"""
        try:
            await self.page.click(selector)
            await self.page.wait_for_load_state("networkidle", timeout=5000)
            return {"success": True}
        except Exception as e:
            return {"error": str(e)}

    async def get_screenshot(self, path: str = None) -> Dict:
        """Take screenshot of current page"""
        if path is None:
            path = f"/tmp/browser_{int(time.time())}.png"

        try:
            await self.page.screenshot(path=path)

            with open(path, "rb") as f:
                import base64

                img_b64 = base64.b64encode(f.read()).decode()

            return {"success": True, "path": path, "base64": img_b64[:100] + "..."}
        except Exception as e:
            return {"error": str(e)}

    async def extract_table(self, selector: str = "table") -> Dict:
        """Extract table data"""
        try:
            table = await self.page.query_selector(selector)
            if not table:
                return {"error": "No table found"}

            rows = await table.query_selector_all("tr")
            data = []

            for row in rows:
                cells = await row.query_selector_all("th, td")
                row_data = [await c.inner_text() for c in cells]
                data.append(row_data)

            return {"table": data, "rows": len(data)}
        except Exception as e:
            return {"error": str(e)}

    async def execute_script(self, script: str) -> Dict:
        """Execute JavaScript in page context"""
        try:
            result = await self.page.evaluate(script)
            return {"result": str(result)[:1000]}
        except Exception as e:
            return {"error": str(e)}

    async def navigate_and_wait(self, url: str, selector: str = None) -> Dict:
        """Navigate to URL and wait for element"""
        try:
            await self.page.goto(url, timeout=self.config.timeout)

            if selector:
                await self.page.wait_for_selector(selector, timeout=10000)

            return {"success": True, "url": url}
        except Exception as e:
            return {"error": str(e)}


class SimpleWebSearch:
    """
    Simple web search without browser (fallback)
    Uses DuckDuckGo HTML results
    """

    def __init__(self):
        self.session = None

    async def search(self, query: str, num_results: int = 5) -> Dict:
        """Simple web search"""
        try:
            import requests

            url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"

            response = requests.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                },
                timeout=10,
            )

            results = []

            # Parse results (simple regex)
            import re

            result_pattern = r'<a class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>.*?<a class="result__snippet"[^>]*>([^<]*)'

            matches = re.findall(result_pattern, response.text)

            for url, title, snippet in matches[:num_results]:
                results.append(
                    {
                        "title": title.strip()[:200],
                        "url": url.strip()[:300],
                        "snippet": snippet.strip()[:300],
                    }
                )

            return {"results": results, "query": query, "count": len(results)}

        except Exception as e:
            return {"error": str(e), "query": query}


# Global instances
_browser_automation: Optional[BrowserAutomationBridge] = None
_simple_search: Optional[SimpleWebSearch] = None


def get_browser_automation() -> BrowserAutomationBridge:
    global _browser_automation
    if _browser_automation is None:
        _browser_automation = BrowserAutomationBridge()
    return _browser_automation


def get_simple_search() -> SimpleWebSearch:
    global _simple_search
    if _simple_search is None:
        _simple_search = SimpleWebSearch()
    return _simple_search


async def web_search(query: str, num_results: int = 5) -> Dict:
    """Quick web search function"""
    # Try simple search first (no browser needed)
    search = get_simple_search()
    return await search.search(query, num_results)


if __name__ == "__main__":

    async def test():
        # Test simple search
        search = SimpleWebSearch()
        results = await search.search("AI agents 2026")
        print(json.dumps(results, indent=2)[:500])

    asyncio.run(test())
