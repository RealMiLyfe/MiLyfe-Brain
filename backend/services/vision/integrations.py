"""
External Integrations Hub - Jira, Linear, Slack, Discord, Calendar.

Provides a unified interface for connecting MiLyfe Brain to external
services for bidirectional communication.
"""

import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx


class IntegrationProvider(str, Enum):
    JIRA = "jira"
    LINEAR = "linear"
    SLACK = "slack"
    DISCORD = "discord"
    GITHUB = "github"
    CALENDAR = "calendar"


@dataclass
class IntegrationConfig:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    provider: IntegrationProvider = IntegrationProvider.SLACK
    name: str = ""
    credentials: Dict[str, str] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    status: str = "active"
    last_sync: Optional[datetime] = None


class BaseIntegration(ABC):
    """Base class for all integrations."""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self._client = httpx.AsyncClient(timeout=30)

    @abstractmethod
    async def test_connection(self) -> bool: ...

    @abstractmethod
    async def sync(self) -> Dict[str, Any]: ...

    async def close(self):
        await self._client.aclose()


class SlackIntegration(BaseIntegration):
    """Slack integration for notifications and commands."""

    async def test_connection(self) -> bool:
        token = self.config.credentials.get("bot_token", "")
        resp = await self._client.get(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {token}"},
        )
        return resp.json().get("ok", False)

    async def sync(self) -> Dict[str, Any]:
        return {"status": "synced", "channels": []}

    async def send_message(self, channel: str, text: str, blocks: Optional[List] = None) -> bool:
        token = self.config.credentials.get("bot_token", "")
        payload: Dict[str, Any] = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = blocks
        resp = await self._client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        return resp.json().get("ok", False)


class DiscordIntegration(BaseIntegration):
    """Discord integration via webhook or bot."""

    async def test_connection(self) -> bool:
        webhook_url = self.config.credentials.get("webhook_url", "")
        if webhook_url:
            resp = await self._client.get(webhook_url)
            return resp.status_code == 200
        return False

    async def sync(self) -> Dict[str, Any]:
        return {"status": "synced"}

    async def send_message(self, content: str, embed: Optional[Dict] = None) -> bool:
        webhook_url = self.config.credentials.get("webhook_url", "")
        payload: Dict[str, Any] = {"content": content, "username": "MiLyfe Brain"}
        if embed:
            payload["embeds"] = [embed]
        resp = await self._client.post(webhook_url, json=payload)
        return resp.status_code in (200, 204)


class JiraIntegration(BaseIntegration):
    """Jira integration for issue tracking."""

    async def test_connection(self) -> bool:
        base_url = self.config.credentials.get("base_url", "")
        email = self.config.credentials.get("email", "")
        token = self.config.credentials.get("api_token", "")
        resp = await self._client.get(
            f"{base_url}/rest/api/3/myself",
            auth=(email, token),
        )
        return resp.status_code == 200

    async def sync(self) -> Dict[str, Any]:
        return {"status": "synced", "projects": []}

    async def create_issue(self, project: str, summary: str, description: str, issue_type: str = "Task") -> Optional[str]:
        base_url = self.config.credentials.get("base_url", "")
        email = self.config.credentials.get("email", "")
        token = self.config.credentials.get("api_token", "")
        resp = await self._client.post(
            f"{base_url}/rest/api/3/issue",
            auth=(email, token),
            json={"fields": {"project": {"key": project}, "summary": summary, "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]}, "issuetype": {"name": issue_type}}},
        )
        if resp.status_code == 201:
            return resp.json().get("key")
        return None


class LinearIntegration(BaseIntegration):
    """Linear integration for issue tracking."""

    async def test_connection(self) -> bool:
        token = self.config.credentials.get("api_key", "")
        resp = await self._client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": token},
            json={"query": "{ viewer { id name } }"},
        )
        return resp.status_code == 200

    async def sync(self) -> Dict[str, Any]:
        return {"status": "synced", "teams": []}

    async def create_issue(self, team_id: str, title: str, description: str) -> Optional[str]:
        token = self.config.credentials.get("api_key", "")
        mutation = """mutation($input: IssueCreateInput!) { issueCreate(input: $input) { issue { id identifier } } }"""
        resp = await self._client.post(
            "https://api.linear.app/graphql",
            headers={"Authorization": token},
            json={"query": mutation, "variables": {"input": {"teamId": team_id, "title": title, "description": description}}},
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", {}).get("issueCreate", {}).get("issue", {}).get("identifier")
        return None


class CalendarIntegration(BaseIntegration):
    """Calendar awareness for scheduling context."""

    async def test_connection(self) -> bool:
        return True  # Local calendar doesn't need connection test

    async def sync(self) -> Dict[str, Any]:
        return {"status": "synced", "events": []}

    async def get_today_events(self) -> List[Dict]:
        """Get today's calendar events for context injection."""
        # Placeholder - would integrate with Google Calendar / Apple Calendar
        return []

    async def create_event(self, title: str, start: str, end: str, description: str = "") -> bool:
        return True


class IntegrationHub:
    """Central hub for managing all integrations."""

    def __init__(self):
        self._integrations: Dict[str, BaseIntegration] = {}
        self._configs: Dict[str, IntegrationConfig] = {}

    def register(self, config: IntegrationConfig) -> str:
        """Register a new integration."""
        self._configs[config.id] = config
        integration = self._create_integration(config)
        if integration:
            self._integrations[config.id] = integration
        return config.id

    def _create_integration(self, config: IntegrationConfig) -> Optional[BaseIntegration]:
        """Factory for creating integration instances."""
        factories = {
            IntegrationProvider.SLACK: SlackIntegration,
            IntegrationProvider.DISCORD: DiscordIntegration,
            IntegrationProvider.JIRA: JiraIntegration,
            IntegrationProvider.LINEAR: LinearIntegration,
            IntegrationProvider.CALENDAR: CalendarIntegration,
        }
        factory = factories.get(config.provider)
        if factory:
            return factory(config)
        return None

    def get(self, integration_id: str) -> Optional[BaseIntegration]:
        return self._integrations.get(integration_id)

    def list_all(self) -> List[Dict[str, Any]]:
        return [
            {"id": c.id, "provider": c.provider.value, "name": c.name, "status": c.status}
            for c in self._configs.values()
        ]

    async def test_all(self) -> Dict[str, bool]:
        results = {}
        for id_, integration in self._integrations.items():
            try:
                results[id_] = await integration.test_connection()
            except Exception:
                results[id_] = False
        return results


# Singleton
integration_hub = IntegrationHub()
