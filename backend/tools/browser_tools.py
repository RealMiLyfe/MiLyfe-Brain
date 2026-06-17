"""Browser Tools — Playwright web automation."""

from typing import Optional


async def web_browse(url: str, action: str = "get_content", selector: Optional[str] = None) -> str:
    """Browse a web page using Playwright.

    Args:
        url: URL to navigate to
        action: get_content, screenshot, click, fill
        selector: CSS selector for interactions
    """
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)

            if action == "get_content":
                content = await page.content()
                text = await page.inner_text("body")
                # Truncate
                if len(text) > 10000:
                    text = text[:10000] + "\n...[truncated]"
                result = f"URL: {url}\nTitle: {await page.title()}\n\n{text}"

            elif action == "screenshot":
                screenshot = await page.screenshot()
                result = f"Screenshot taken ({len(screenshot)} bytes)"

            elif action == "click" and selector:
                await page.click(selector)
                result = f"Clicked: {selector}"

            elif action == "fill" and selector:
                # selector should include the value to fill
                result = f"Fill action requires value parameter"

            else:
                result = f"Unknown action: {action}"

            await browser.close()
            return result

    except Exception as e:
        return f"Browser error: {str(e)}"


async def web_search(query: str, num_results: int = 5) -> str:
    """Search the web (simplified — fetches from DuckDuckGo lite)."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://lite.duckduckgo.com/lite/",
                params={"q": query},
                headers={"User-Agent": "Mozilla/5.0 (compatible; MiLyfe/1.0)"},
            )
            if resp.status_code == 200:
                # Basic text extraction
                text = resp.text
                # Simple extraction of results
                results = f"Search results for: {query}\n"
                results += f"(Status: {resp.status_code}, Length: {len(text)} chars)\n"
                results += "Use web_browse for detailed page content."
                return results
            else:
                return f"Search failed: HTTP {resp.status_code}"
    except Exception as e:
        return f"Search error: {str(e)}"


def register_browser_tools(registry):
    """Register browser tools with the tool registry."""
    registry.register("web_browse", "Browse web page (Playwright)", web_browse, permission="approve",
                      params={"url": "URL to browse", "action": "Action: get_content/screenshot/click", "selector": "CSS selector"})
    registry.register("web_search", "Search the web", web_search, permission="notify",
                      params={"query": "Search query", "num_results": "Number of results"})
