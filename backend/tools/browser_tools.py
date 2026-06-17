"""Browser and web tools for MiLyfe Brain.

These are stubs that require playwright installation for full functionality.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def web_browse(url: str, action: str = "get") -> str:
    """Browse a URL and return page content.

    Args:
        url: The URL to navigate to.
        action: Browser action (get, click, type, scroll).

    Returns:
        Stub message indicating playwright is required.
    """
    logger.info("web_browse: url=%s action=%s (stub)", url, action)
    return (
        "Browser tools require playwright installation. "
        "Install with: pip install playwright && playwright install chromium\n"
        f"Requested: {action} {url}"
    )


async def web_search(query: str) -> str:
    """Search the web and return results.

    Args:
        query: Search query string.

    Returns:
        Stub message indicating playwright is required.
    """
    logger.info("web_search: query=%r (stub)", query)
    return (
        "Browser tools require playwright installation. "
        "Install with: pip install playwright && playwright install chromium\n"
        f"Requested search: {query}"
    )
