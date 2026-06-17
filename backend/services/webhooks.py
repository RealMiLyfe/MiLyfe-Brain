"""
MiLyfe Brain - Webhooks Service

Manages outgoing webhooks, incoming webhook handlers, and event triggers.
Enables integration with external services via HTTP callbacks.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Registry of outgoing webhooks
_outgoing_webhooks: Dict[str, Dict[str, Any]] = {}

# Registry of incoming webhook handlers
_incoming_handlers: Dict[str, Callable] = {}

# Event trigger mappings (event_type -> list of webhook IDs)
_triggers: Dict[str, List[str]] = {}


async def register_outgoing(
    url: str,
    events: List[str],
    name: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    secret: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Register an outgoing webhook.

    Args:
        url: Target URL to call on events.
        events: List of event types to subscribe to.
        name: Human-readable name for this webhook.
        headers: Optional custom headers to include.
        secret: Optional HMAC secret for payload signing.

    Returns:
        Dict with webhook registration info.
    """
    webhook_id = str(uuid4())

    webhook = {
        "id": webhook_id,
        "name": name or f"webhook-{webhook_id[:8]}",
        "url": url,
        "events": events,
        "headers": headers or {},
        "secret": secret,
        "enabled": True,
        "created_at": datetime.utcnow().isoformat(),
        "last_triggered": None,
        "trigger_count": 0,
    }

    _outgoing_webhooks[webhook_id] = webhook

    # Register triggers
    for event in events:
        if event not in _triggers:
            _triggers[event] = []
        _triggers[event].append(webhook_id)

    logger.info("Outgoing webhook registered: %s -> %s (events: %s)", webhook_id[:8], url, events)
    return {"id": webhook_id, "name": webhook["name"], "url": url, "events": events}


async def emit(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Emit an event, triggering all registered outgoing webhooks.

    Args:
        event_type: Type of event being emitted.
        payload: Event data to send.

    Returns:
        Dict with 'triggered' count and 'results'.
    """
    webhook_ids = _triggers.get(event_type, [])
    results: List[Dict[str, Any]] = []

    for webhook_id in webhook_ids:
        webhook = _outgoing_webhooks.get(webhook_id)
        if webhook is None or not webhook["enabled"]:
            continue

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                headers = dict(webhook.get("headers", {}))
                headers["Content-Type"] = "application/json"
                headers["X-MiLyfe-Event"] = event_type

                response = await client.post(
                    webhook["url"],
                    json={"event": event_type, "payload": payload},
                    headers=headers,
                )

                webhook["last_triggered"] = datetime.utcnow().isoformat()
                webhook["trigger_count"] += 1

                results.append({
                    "webhook_id": webhook_id,
                    "status": response.status_code,
                    "success": 200 <= response.status_code < 300,
                })

        except Exception as e:
            logger.warning("Webhook %s failed: %s", webhook_id[:8], e)
            results.append({
                "webhook_id": webhook_id,
                "status": 0,
                "success": False,
                "error": str(e),
            })

    return {
        "event_type": event_type,
        "triggered": len(results),
        "results": results,
    }


async def handle_incoming(
    hook_name: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Handle an incoming webhook call.

    Args:
        hook_name: Name of the registered handler.
        payload: Incoming webhook payload.
        headers: Request headers.

    Returns:
        Dict with handler result.
    """
    handler = _incoming_handlers.get(hook_name)

    if handler is None:
        logger.warning("No handler registered for incoming webhook: %s", hook_name)
        return {"error": f"No handler for '{hook_name}'", "handled": False}

    try:
        result = handler(payload, headers)
        return {"handled": True, "result": result}
    except Exception as e:
        logger.error("Incoming webhook handler '%s' failed: %s", hook_name, e)
        return {"handled": False, "error": str(e)}


def register_trigger(
    hook_name: str,
    handler: Callable[[Dict[str, Any], Optional[Dict[str, str]]], Any],
) -> None:
    """
    Register a handler for incoming webhooks.

    Args:
        hook_name: Name to register under.
        handler: Callable that processes (payload, headers).
    """
    _incoming_handlers[hook_name] = handler
    logger.info("Incoming webhook handler registered: %s", hook_name)


def list_outgoing() -> List[Dict[str, Any]]:
    """List all registered outgoing webhooks."""
    return [
        {k: v for k, v in wh.items() if k != "secret"}
        for wh in _outgoing_webhooks.values()
    ]
