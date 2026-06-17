"""
MiLyfe Brain - Browser Automation Tools

Web browsing and search using Playwright and DuckDuckGo.
"""
from __future__ import annotations

import asyncio
import re
from typing import Optional, TYPE_CHECKING
from urllib.parse import quote_plus, urljoin

from models.schemas import PermissionLevel

if TYPE_CHECKING:
    from tools.registry import ToolRegistry


async def web_browse(url: str, action: str = "get_text", selector: str = "") -> str:
    """Browse a web page and perform actions using Playwright.

    Args:
        url: URL to navigate to.
        action: Action to perform - get_text, get_html, screenshot, click, fill, evaluate.
        selector: CSS selector for targeted actions (click, fill, evaluate).

    Returns:
        Page content, action result, or error message.
    """
    valid_actions = {"get_text", "get_html", "screenshot", "click", "fill", "evaluate"}
    if action not in valid_actions:
        return f"Error: Invalid action '{action}'. Valid: {', '.join(sorted(valid_actions))}"

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return "Error: Playwright not installed. Install with: pip install playwright && playwright install"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            result = ""

            if action == "get_text":
                result = await page.inner_text("body")
                # Clean up excessive whitespace
                result = re.sub(r"\n{3,}", "\n\n", result)
                if len(result) > 10000:
                    result = result[:10000] + "\n\n... (truncated)"

            elif action == "get_html":
                if selector:
                    element = await page.query_selector(selector)
                    if element:
                        result = await element.inner_html()
                    else:
                        result = f"Error: Selector '{selector}' not found"
                else:
                    result = await page.content()
                if len(result) > 20000:
                    result = result[:20000] + "\n\n... (truncated)"

            elif action == "screenshot":
                screenshot_bytes = await page.screenshot(full_page=False)
                import base64
                encoded = base64.b64encode(screenshot_bytes).decode()
                result = f"Screenshot captured ({len(screenshot_bytes)} bytes, base64 encoded)\ndata:image/png;base64,{encoded[:100]}..."

            elif action == "click":
                if not selector:
                    result = "Error: 'selector' required for click action"
                else:
                    await page.click(selector, timeout=5000)
                    await page.wait_for_load_state("domcontentloaded")
                    result = f"Clicked: {selector}\nCurrent URL: {page.url}"

            elif action == "fill":
                if not selector:
                    result = "Error: 'selector' required for fill action"
                else:
                    # For fill, the selector text is in format "selector|text_to_fill"
                    parts = selector.split("|", 1)
                    if len(parts) == 2:
                        sel, text = parts
                        await page.fill(sel.strip(), text.strip())
                        result = f"Filled '{sel.strip()}' with text"
                    else:
                        result = "Error: For fill, use format 'selector|text_to_fill' in the selector param"

            elif action == "evaluate":
                if not selector:
                    result = "Error: 'selector' required (contains JS expression) for evaluate action"
                else:
                    eval_result = await page.evaluate(selector)
                    result = str(eval_result)

            await browser.close()
            return result

    except Exception as e:
        return f"Browser error: {type(e).__name__}: {e}"


async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo HTML search.

    Args:
        query: Search query string.
        max_results: Maximum number of results to return (1-10).

    Returns:
        Formatted search results with titles, URLs, and snippets.
    """
    max_results = min(max(max_results, 1), 10)
    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return _web_search_fallback(query, max_results)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)

            results = []
            result_elements = await page.query_selector_all(".result")

            for element in result_elements[:max_results]:
                title_el = await element.query_selector(".result__title a")
                snippet_el = await element.query_selector(".result__snippet")

                title = await title_el.inner_text() if title_el else "No title"
                href = await title_el.get_attribute("href") if title_el else ""
                snippet = await snippet_el.inner_text() if snippet_el else ""

                results.append(f"**{title}**\n  URL: {href}\n  {snippet}")

            await browser.close()

            if not results:
                return f"No results found for: {query}"

            return f"Search results for '{query}':\n\n" + "\n\n".join(results)

    except Exception as e:
        return f"Search error: {type(e).__name__}: {e}"


def _web_search_fallback(query: str, max_results: int) -> str:
    """Fallback search using urllib (no Playwright)."""
    try:
        import urllib.request

        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        req = urllib.request.Request(
            search_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MiLyfe/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Basic HTML parsing for results
        results = []
        pattern = r'class="result__title".*?<a.*?href="(.*?)".*?>(.*?)</a>'
        matches = re.findall(pattern, html, re.DOTALL)

        for href, title in matches[:max_results]:
            clean_title = re.sub(r"<.*?>", "", title).strip()
            results.append(f"**{clean_title}**\n  URL: {href}")

        if not results:
            return f"No results found for: {query}"
        return f"Search results for '{query}':\n\n" + "\n\n".join(results)

    except Exception as e:
        return f"Fallback search error: {type(e).__name__}: {e}"


def register_browser_tools(registry: ToolRegistry) -> None:
    """Register browser tools with the tool registry."""
    registry.register(
        name="web_browse",
        handler=web_browse,
        category="browser",
        description="Browse a web page and perform actions (get_text, get_html, screenshot, click, fill, evaluate).",
        parameters={
            "url": {"type": "string", "description": "URL to navigate to", "required": True},
            "action": {"type": "string", "description": "Action: get_text, get_html, screenshot, click, fill, evaluate", "default": "get_text"},
            "selector": {"type": "string", "description": "CSS selector for targeted actions", "default": ""},
        },
        permission=PermissionLevel.DESTRUCTIVE,
        returns="Page content or action result",
    )
    registry.register(
        name="web_search",
        handler=web_search,
        category="browser",
        description="Search the web using DuckDuckGo.",
        parameters={
            "query": {"type": "string", "description": "Search query", "required": True},
            "max_results": {"type": "integer", "description": "Max results (1-10)", "default": 5},
        },
        permission=PermissionLevel.DESTRUCTIVE,
        returns="Formatted search results with titles, URLs, and snippets",
    )
