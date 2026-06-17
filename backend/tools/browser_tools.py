"""MiLyfe Brain — Playwright Web Automation Tools."""

from __future__ import annotations

from models.schemas import PermissionLevel


async def web_browse(url: str, action: str = "get_text", selector: str = "") -> str:
    """Browse a web page using Playwright.

    Actions: get_text, get_html, screenshot, click, fill, evaluate
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return "Error: Playwright not installed"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")

            if action == "get_text":
                content = await page.inner_text("body")
                # Truncate long content
                if len(content) > 8000:
                    content = content[:8000] + "\n...[truncated]..."
                return content

            elif action == "get_html":
                html = await page.content()
                if len(html) > 10000:
                    html = html[:10000] + "\n...[truncated]..."
                return html

            elif action == "screenshot":
                path = "/workspace/.screenshots/latest.png"
                import os
                os.makedirs("/workspace/.screenshots", exist_ok=True)
                await page.screenshot(path=path, full_page=False)
                return f"Screenshot saved: {path}"

            elif action == "click" and selector:
                await page.click(selector, timeout=5000)
                return f"Clicked: {selector}"

            elif action == "fill" and selector:
                parts = selector.split("|", 1)
                if len(parts) == 2:
                    await page.fill(parts[0], parts[1], timeout=5000)
                    return f"Filled {parts[0]} with text"
                return "Error: fill requires 'selector|text' format"

            elif action == "evaluate":
                result = await page.evaluate(selector or "document.title")
                return str(result)

            else:
                return f"Unknown action: {action}"

        except Exception as e:
            return f"Browser error: {e}"
        finally:
            await browser.close()


async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web (uses DuckDuckGo HTML)."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": "MiLyfe-Brain/1.0"},
            )

            if resp.status_code != 200:
                return f"Search failed: HTTP {resp.status_code}"

            # Parse results from HTML
            import re
            results = []
            links = re.findall(
                r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.+?)</a>',
                resp.text,
            )
            snippets = re.findall(
                r'<a class="result__snippet"[^>]*>(.+?)</a>',
                resp.text,
            )

            for i, (url, title) in enumerate(links[:max_results]):
                title_clean = re.sub(r"<[^>]+>", "", title).strip()
                snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip() if i < len(snippets) else ""
                results.append(f"{i+1}. {title_clean}\n   {url}\n   {snippet}")

            return "\n\n".join(results) if results else "No results found"

    except Exception as e:
        return f"Search error: {e}"


def register_browser_tools(registry):
    """Register browser tools."""
    registry.register(
        name="web_browse",
        handler=web_browse,
        category="Browser",
        description="Browse web pages (get_text, screenshot, click, fill)",
        parameters={"url": "str", "action": "str", "selector": "str"},
        permission=PermissionLevel.APPROVE,
    )
    registry.register(
        name="web_search",
        handler=web_search,
        category="Browser",
        description="Search the web via DuckDuckGo",
        parameters={"query": "str", "max_results": "int"},
        permission=PermissionLevel.NOTIFY,
    )
