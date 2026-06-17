"""MiLyfe Brain — Inter-Agent Topic-Based Message Bus."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List

import structlog

logger = structlog.get_logger()


class MessageBus:
    """Topic-based pub/sub for inter-agent communication."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._history: List[Dict[str, Any]] = []
        self._max_history: int = 500

    def subscribe(self, topic: str, callback: Callable):
        """Subscribe to a topic."""
        self._subscribers[topic].append(callback)

    def unsubscribe(self, topic: str, callback: Callable):
        """Unsubscribe from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic] = [
                cb for cb in self._subscribers[topic] if cb != callback
            ]

    async def publish(self, topic: str, data: Dict[str, Any]):
        """Publish a message to a topic."""
        message = {
            "topic": topic,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Store in history
        self._history.append(message)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Notify subscribers (exact match + wildcard)
        notified = 0
        for pattern, callbacks in self._subscribers.items():
            if self._matches(pattern, topic):
                for cb in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(cb):
                            await cb(message)
                        else:
                            cb(message)
                        notified += 1
                    except Exception as e:
                        logger.error("bus_callback_error",
                                     topic=topic, error=str(e))

        # Also publish to Redis for cross-process support
        await self._publish_redis(topic, data)

    async def _publish_redis(self, topic: str, data: Dict[str, Any]):
        """Publish to Redis PubSub (optional, for multi-process)."""
        try:
            import redis.asyncio as aioredis
            import orjson
            from config import settings
            r = aioredis.from_url(settings.redis_url)
            await r.publish(
                f"milyfe:{topic}",
                orjson.dumps(data),
            )
            await r.close()
        except Exception:
            pass  # Redis is optional

    def get_history(
        self, topic: str | None = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get message history, optionally filtered by topic."""
        if topic:
            filtered = [m for m in self._history
                        if self._matches(topic, m["topic"])]
            return filtered[-limit:]
        return self._history[-limit:]

    @staticmethod
    def _matches(pattern: str, topic: str) -> bool:
        """Check if topic matches pattern (supports * wildcard)."""
        if pattern == topic:
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return topic.startswith(prefix)
        if pattern == "*":
            return True
        return False


# Singleton
message_bus = MessageBus()
