"""MiLyfe Brain — Integration Webhooks.

Git triggers, file watcher rules, output hooks to external services.
Incoming webhooks (receive events) + Outgoing webhooks (notify external).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()


# ─── Webhook Definitions ───────────────────────────────────────


class OutgoingWebhook:
    """Configuration for sending events to external services."""

    def __init__(
        self,
        id: str,
        name: str,
        url: str,
        events: List[str],
        secret: str = "",
        enabled: bool = True,
        headers: Dict[str, str] = None,
        retry_count: int = 3,
    ):
        self.id = id
        self.name = name
        self.url = url
        self.events = events  # ["playbook.completed", "playbook.failed", "approval.required"]
        self.secret = secret
        self.enabled = enabled
        self.headers = headers or {}
        self.retry_count = retry_count
        self.last_triggered: Optional[datetime] = None
        self.total_sent: int = 0
        self.total_failures: int = 0


class IncomingWebhook:
    """Configuration for receiving events from external services."""

    def __init__(
        self,
        id: str,
        name: str,
        token: str,
        action: str,
        action_config: Dict[str, Any] = None,
        enabled: bool = True,
    ):
        self.id = id
        self.name = name
        self.token = token  # Authentication token
        self.action = action  # "run_playbook", "trigger_chat", "notify"
        self.action_config = action_config or {}
        self.enabled = enabled
        self.last_received: Optional[datetime] = None
        self.total_received: int = 0


class TriggerRule:
    """A rule that triggers actions based on events."""

    def __init__(
        self,
        id: str,
        name: str,
        source: str,  # "git", "file", "schedule", "webhook"
        condition: Dict[str, Any] = None,
        action: str = "run_playbook",
        action_config: Dict[str, Any] = None,
        enabled: bool = True,
        cooldown_seconds: int = 60,
    ):
        self.id = id
        self.name = name
        self.source = source
        self.condition = condition or {}
        self.action = action
        self.action_config = action_config or {}
        self.enabled = enabled
        self.cooldown_seconds = cooldown_seconds
        self.last_triggered: Optional[datetime] = None


# ─── Webhook Service ────────────────────────────────────────────


class WebhookService:
    """Manages incoming/outgoing webhooks and trigger rules."""

    def __init__(self):
        self._outgoing: Dict[str, OutgoingWebhook] = {}
        self._incoming: Dict[str, IncomingWebhook] = {}
        self._trigger_rules: Dict[str, TriggerRule] = {}
        self._event_log: List[Dict] = []

        # Register built-in trigger rules
        self._register_defaults()

    # ─── Outgoing Webhooks ──────────────────────────────────────

    def register_outgoing(
        self,
        name: str,
        url: str,
        events: List[str],
        secret: str = "",
        headers: Dict[str, str] = None,
    ) -> str:
        """Register a new outgoing webhook."""
        hook_id = str(uuid.uuid4())[:12]
        self._outgoing[hook_id] = OutgoingWebhook(
            id=hook_id,
            name=name,
            url=url,
            events=events,
            secret=secret,
            headers=headers,
        )
        logger.info("outgoing_webhook_registered", id=hook_id, name=name, events=events)
        return hook_id

    def remove_outgoing(self, hook_id: str):
        """Remove an outgoing webhook."""
        self._outgoing.pop(hook_id, None)

    async def emit(self, event_type: str, payload: Dict[str, Any]):
        """Emit an event to all matching outgoing webhooks."""
        for hook in self._outgoing.values():
            if not hook.enabled:
                continue
            if event_type in hook.events or "*" in hook.events:
                asyncio.create_task(self._send_webhook(hook, event_type, payload))

    async def _send_webhook(self, hook: OutgoingWebhook, event_type: str, payload: Dict):
        """Send a webhook with retry logic."""
        import orjson

        body = orjson.dumps({
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
            "webhook_id": hook.id,
        })

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MiLyfe-Brain/1.0",
            "X-Webhook-Event": event_type,
            "X-Webhook-ID": hook.id,
            **hook.headers,
        }

        # HMAC signature if secret configured
        if hook.secret:
            signature = hmac.new(
                hook.secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        for attempt in range(hook.retry_count):
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(hook.url, content=body, headers=headers)

                    if resp.status_code < 400:
                        hook.last_triggered = datetime.utcnow()
                        hook.total_sent += 1
                        self._log_event("outgoing", hook.name, event_type, "success")
                        return

                    if resp.status_code >= 500 and attempt < hook.retry_count - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue

                    hook.total_failures += 1
                    self._log_event("outgoing", hook.name, event_type, f"failed:{resp.status_code}")
                    return

            except Exception as e:
                if attempt < hook.retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                hook.total_failures += 1
                self._log_event("outgoing", hook.name, event_type, f"error:{e}")

    # ─── Incoming Webhooks ──────────────────────────────────────

    def register_incoming(
        self,
        name: str,
        action: str,
        action_config: Dict = None,
    ) -> Dict[str, str]:
        """Register a new incoming webhook. Returns ID and token."""
        hook_id = str(uuid.uuid4())[:12]
        token = str(uuid.uuid4())

        self._incoming[hook_id] = IncomingWebhook(
            id=hook_id,
            name=name,
            token=token,
            action=action,
            action_config=action_config or {},
        )
        logger.info("incoming_webhook_registered", id=hook_id, name=name)
        return {"id": hook_id, "token": token, "url": f"/api/webhooks/incoming/{hook_id}"}

    async def handle_incoming(self, hook_id: str, token: str, payload: Dict) -> Dict:
        """Handle an incoming webhook event."""
        hook = self._incoming.get(hook_id)
        if not hook:
            return {"error": "Webhook not found"}
        if hook.token != token:
            return {"error": "Invalid token"}
        if not hook.enabled:
            return {"error": "Webhook disabled"}

        hook.last_received = datetime.utcnow()
        hook.total_received += 1
        self._log_event("incoming", hook.name, hook.action, "received")

        # Execute action
        return await self._execute_action(hook.action, hook.action_config, payload)

    # ─── Trigger Rules ──────────────────────────────────────────

    def register_trigger(
        self,
        name: str,
        source: str,
        condition: Dict = None,
        action: str = "run_playbook",
        action_config: Dict = None,
        cooldown_seconds: int = 60,
    ) -> str:
        """Register a trigger rule."""
        rule_id = str(uuid.uuid4())[:12]
        self._trigger_rules[rule_id] = TriggerRule(
            id=rule_id,
            name=name,
            source=source,
            condition=condition or {},
            action=action,
            action_config=action_config or {},
            cooldown_seconds=cooldown_seconds,
        )
        return rule_id

    async def process_event(self, source: str, event_data: Dict):
        """Process an event against all trigger rules."""
        now = datetime.utcnow()

        for rule in self._trigger_rules.values():
            if not rule.enabled or rule.source != source:
                continue

            # Check cooldown
            if rule.last_triggered:
                elapsed = (now - rule.last_triggered).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue

            # Check condition
            if self._matches_condition(rule.condition, event_data):
                rule.last_triggered = now
                self._log_event("trigger", rule.name, rule.action, "triggered")
                asyncio.create_task(
                    self._execute_action(rule.action, rule.action_config, event_data)
                )

    # ─── Git Integration Triggers ───────────────────────────────

    async def process_git_event(self, event_type: str, data: Dict):
        """Process a git-related event (push, PR, etc.)."""
        await self.process_event("git", {
            "git_event": event_type,
            **data,
        })

        # Also emit as outgoing webhook
        await self.emit(f"git.{event_type}", data)

    # ─── Action Execution ───────────────────────────────────────

    async def _execute_action(self, action: str, config: Dict, payload: Dict) -> Dict:
        """Execute a triggered action."""
        try:
            if action == "run_playbook":
                playbook_id = config.get("playbook_id")
                if playbook_id:
                    from graphs.orchestrator import execute_playbook
                    asyncio.create_task(execute_playbook(playbook_id))
                    return {"executed": "run_playbook", "playbook_id": playbook_id}
                else:
                    # Create and run a new playbook from payload
                    title = payload.get("title", config.get("title", "Webhook Triggered"))
                    description = payload.get("description", config.get("description", str(payload)))
                    from api.routes.playbooks import _execute_playbook
                    # Would create playbook here
                    return {"executed": "run_playbook", "title": title}

            elif action == "trigger_chat":
                message = config.get("message", payload.get("message", ""))
                if message:
                    from agents.factory import agent_factory
                    result = await agent_factory.chat(message=message, session_id="webhook")
                    return {"executed": "chat", "response": result.get("content", "")[:200]}

            elif action == "notify":
                title = config.get("title", "Webhook Notification")
                message = config.get("message", str(payload)[:200])
                from services.notification_service import notification_service
                await notification_service.push(title=title, message=message, type="info")
                return {"executed": "notify", "title": title}

            elif action == "emit_event":
                event_type = config.get("event_type", "webhook.received")
                from api.routes.streaming import emit_event
                from models.schemas import EventType
                emit_event(event_type=EventType.PROGRESS, data={"webhook": payload})
                return {"executed": "emit_event"}

            return {"error": f"Unknown action: {action}"}

        except Exception as e:
            logger.error("webhook_action_failed", action=action, error=str(e))
            return {"error": str(e)}

    # ─── Condition Matching ─────────────────────────────────────

    def _matches_condition(self, condition: Dict, event_data: Dict) -> bool:
        """Check if event data matches a trigger condition."""
        if not condition:
            return True  # No condition = always match

        for key, expected in condition.items():
            actual = event_data.get(key)

            if isinstance(expected, str):
                if expected.startswith("contains:"):
                    needle = expected[9:]
                    if needle not in str(actual):
                        return False
                elif expected.startswith("regex:"):
                    import re
                    if not re.search(expected[6:], str(actual)):
                        return False
                elif str(actual) != expected:
                    return False
            elif isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False

        return True

    # ─── Default Triggers ───────────────────────────────────────

    def _register_defaults(self):
        """Register built-in trigger rules."""
        # Notify on playbook completion
        self.register_trigger(
            name="notify_on_complete",
            source="internal",
            condition={"event": "playbook.completed"},
            action="notify",
            action_config={"title": "Playbook Completed", "message": "A playbook finished successfully"},
            cooldown_seconds=5,
        )

    # ─── Event Log ──────────────────────────────────────────────

    def _log_event(self, direction: str, name: str, event_type: str, status: str):
        """Log a webhook event."""
        self._event_log.append({
            "direction": direction,
            "name": name,
            "event": event_type,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
        })
        # Keep bounded
        if len(self._event_log) > 500:
            self._event_log = self._event_log[-500:]

    # ─── API ────────────────────────────────────────────────────

    def list_outgoing(self) -> List[Dict]:
        """List all outgoing webhooks."""
        return [
            {
                "id": h.id, "name": h.name, "url": h.url,
                "events": h.events, "enabled": h.enabled,
                "total_sent": h.total_sent, "total_failures": h.total_failures,
                "last_triggered": h.last_triggered.isoformat() if h.last_triggered else None,
            }
            for h in self._outgoing.values()
        ]

    def list_incoming(self) -> List[Dict]:
        """List all incoming webhooks (tokens hidden)."""
        return [
            {
                "id": h.id, "name": h.name, "action": h.action,
                "enabled": h.enabled, "total_received": h.total_received,
                "last_received": h.last_received.isoformat() if h.last_received else None,
            }
            for h in self._incoming.values()
        ]

    def list_triggers(self) -> List[Dict]:
        """List all trigger rules."""
        return [
            {
                "id": r.id, "name": r.name, "source": r.source,
                "action": r.action, "enabled": r.enabled,
                "cooldown_seconds": r.cooldown_seconds,
                "last_triggered": r.last_triggered.isoformat() if r.last_triggered else None,
            }
            for r in self._trigger_rules.values()
        ]

    def get_event_log(self, limit: int = 50) -> List[Dict]:
        """Get recent webhook event log."""
        return self._event_log[-limit:]


# Singleton
webhook_service = WebhookService()
