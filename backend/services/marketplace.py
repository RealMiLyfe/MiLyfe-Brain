"""
MiLyfe Brain - Marketplace Service

Provides access to a community playbook marketplace.
Supports browsing, searching, and installing shared playbooks.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# In-memory index (would be backed by remote API in production)
_MARKETPLACE_INDEX: List[Dict[str, Any]] = [
    {
        "id": "community-web-scraper",
        "title": "Web Scraper Playbook",
        "description": "Automated web scraping with data extraction and CSV export.",
        "author": "community",
        "version": "1.0.0",
        "tags": ["scraping", "data", "automation"],
        "downloads": 142,
    },
    {
        "id": "community-code-review",
        "title": "Code Review Assistant",
        "description": "Automated code review with security and style checks.",
        "author": "community",
        "version": "1.2.0",
        "tags": ["code", "review", "quality"],
        "downloads": 89,
    },
]


async def get_index(page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """
    Get the marketplace index (paginated).

    Args:
        page: Page number (1-based).
        per_page: Items per page.

    Returns:
        Dict with 'items', 'total', 'page', 'per_page'.
    """
    start = (page - 1) * per_page
    end = start + per_page
    items = _MARKETPLACE_INDEX[start:end]

    return {
        "items": items,
        "total": len(_MARKETPLACE_INDEX),
        "page": page,
        "per_page": per_page,
    }


async def search(query: str, tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Search the marketplace for playbooks.

    Args:
        query: Search query text.
        tags: Optional tag filters.

    Returns:
        List of matching playbook entries.
    """
    query_lower = query.lower()
    results = []

    for item in _MARKETPLACE_INDEX:
        text = f"{item['title']} {item['description']}".lower()
        if query_lower in text:
            results.append(item)
            continue
        if tags:
            if any(tag in item.get("tags", []) for tag in tags):
                results.append(item)

    return results


async def install_playbook(marketplace_id: str) -> Dict[str, Any]:
    """
    Install a playbook from the marketplace.

    Args:
        marketplace_id: ID of the marketplace playbook.

    Returns:
        Dict with 'success', 'playbook_id', 'message'.
    """
    # Find in index
    item = next(
        (i for i in _MARKETPLACE_INDEX if i["id"] == marketplace_id),
        None,
    )

    if item is None:
        return {
            "success": False,
            "playbook_id": None,
            "message": f"Playbook '{marketplace_id}' not found in marketplace.",
        }

    # In production, this would download and create the playbook
    logger.info("Installing marketplace playbook: %s", marketplace_id)

    return {
        "success": True,
        "playbook_id": None,  # Would be the new local playbook ID
        "message": f"Playbook '{item['title']}' installed successfully.",
    }
