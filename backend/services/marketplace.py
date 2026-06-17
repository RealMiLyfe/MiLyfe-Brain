"""MiLyfe Brain — Playbook / Skill / Plugin Marketplace.

GitHub-based registry for community sharing (no cloud required).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()

# Default marketplace index URL (GitHub-hosted JSON)
MARKETPLACE_INDEX_URL = "https://raw.githubusercontent.com/milyfe/marketplace/main/index.json"


class MarketplaceService:
    """Community marketplace for playbooks, skills, and plugins."""

    def __init__(self):
        self._cache: Dict = {}
        self._local_dir = Path(settings.workspace_dir) / ".marketplace"

    async def get_index(self) -> Dict:
        """Fetch marketplace index (cached)."""
        if self._cache:
            return self._cache

        # Try remote first
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(MARKETPLACE_INDEX_URL)
                if resp.status_code == 200:
                    self._cache = resp.json()
                    return self._cache
        except Exception:
            pass

        # Fallback to local index
        local_index = self._local_dir / "index.json"
        if local_index.exists():
            self._cache = json.loads(local_index.read_text())
            return self._cache

        # Return default empty index
        return {
            "playbooks": self._get_builtin_playbooks(),
            "skills": self._get_builtin_skills(),
            "plugins": [],
            "version": "1.0",
        }

    async def search(self, query: str, category: str = "") -> List[Dict]:
        """Search marketplace items."""
        index = await self.get_index()
        results = []
        query_lower = query.lower()

        for category_name in ["playbooks", "skills", "plugins"]:
            if category and category != category_name:
                continue
            items = index.get(category_name, [])
            for item in items:
                name = item.get("name", "").lower()
                desc = item.get("description", "").lower()
                tags = " ".join(item.get("tags", [])).lower()
                if query_lower in name or query_lower in desc or query_lower in tags:
                    results.append({**item, "category": category_name})

        return results

    async def install_playbook(self, playbook_id: str) -> Dict:
        """Install a playbook from marketplace."""
        index = await self.get_index()
        playbooks = index.get("playbooks", [])
        pb = next((p for p in playbooks if p.get("id") == playbook_id), None)
        if not pb:
            raise ValueError(f"Playbook not found: {playbook_id}")

        # Save locally
        self._local_dir.mkdir(parents=True, exist_ok=True)
        dest = self._local_dir / "playbooks" / f"{playbook_id}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(pb, indent=2))

        return {"installed": True, "id": playbook_id, "name": pb.get("name")}

    async def publish_playbook(self, playbook_data: Dict) -> Dict:
        """Publish a playbook to local marketplace (for sharing)."""
        self._local_dir.mkdir(parents=True, exist_ok=True)
        published_dir = self._local_dir / "published"
        published_dir.mkdir(exist_ok=True)

        filename = playbook_data.get("title", "untitled").replace(" ", "_").lower()
        dest = published_dir / f"{filename}.json"
        dest.write_text(json.dumps(playbook_data, indent=2))

        return {"published": True, "path": str(dest)}

    def _get_builtin_playbooks(self) -> List[Dict]:
        """Built-in playbook templates."""
        return [
            {"id": "rest_api", "name": "Build REST API", "description": "Full CRUD REST API with FastAPI", "tags": ["api", "python", "fastapi"], "complexity": "medium"},
            {"id": "react_app", "name": "React Dashboard", "description": "Interactive dashboard with React + charts", "tags": ["frontend", "react", "dashboard"], "complexity": "heavy"},
            {"id": "docker_deploy", "name": "Dockerize Project", "description": "Add Docker + docker-compose to any project", "tags": ["docker", "devops", "deploy"], "complexity": "medium"},
            {"id": "test_suite", "name": "Test Suite Generator", "description": "Generate comprehensive test suite for existing code", "tags": ["testing", "pytest", "quality"], "complexity": "medium"},
            {"id": "code_review", "name": "Security Audit", "description": "Full security review of a codebase", "tags": ["security", "audit", "review"], "complexity": "heavy"},
            {"id": "docs_gen", "name": "Documentation Generator", "description": "Generate full docs from source code", "tags": ["docs", "readme", "api-docs"], "complexity": "light"},
        ]

    def _get_builtin_skills(self) -> List[Dict]:
        """Built-in skills."""
        return [
            {"id": "api_design", "name": "API Design", "description": "RESTful API design patterns", "tags": ["api", "rest"]},
            {"id": "error_handling", "name": "Error Handling", "description": "Production error handling patterns", "tags": ["errors", "exceptions"]},
            {"id": "testing", "name": "Testing Best Practices", "description": "Unit/integration test patterns", "tags": ["testing", "quality"]},
        ]


# Singleton
marketplace_service = MarketplaceService()
