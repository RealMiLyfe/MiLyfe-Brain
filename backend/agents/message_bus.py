"""
MiLyfe Brain - Message Bus

Singleton pub/sub message bus for inter-agent communication.
Supports wildcard topic matching and Redis publishing for distributed setups.
"""
from __future__ import annotations

import asyncio
import fnmatch
import logging
import time
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Type alias for subscriber callbacks
SubscriberCallback = Callable[[str, Dict[str, Any]], Union[None, Coroutine[Any, Any, None]]]


class MessageBus:
    """
    Singleton pub/sub message bus.

    Features:
    - Topic-based publish/subscribe with wildcard support
    - Message history (last 500 messages)
    - Optional Redis publishing for distributed deployments
    - Async-safe subscriber notification
    """

    _instance: Optional[MessageBus] = None
    _MAX_HISTORY = 500

    def __new__(cls) -> MessageBus:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers = {}
            cls._instance._history = []
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._subscribers: Dict[str, List[SubscriberCallback]] = {}
            self._history: List[Dict[str, Any]] = []
            self._initialized = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def subscribe(self, topic: str, callback: SubscriberCallback) -> None:
        """
        Subscribe a callback to a topic pattern.

        Topic patterns support:
        - Exact match: "agent.coder.completed"
        - Wildcard: "agent.*.completed"
        - Prefix: "agent.*" (matches all agent topics)
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        if callback not in self._subscribers[topic]:
            self._subscribers[topic].append(callback)
            logger.debug(f"Subscribed to topic: {topic}")

    def unsubscribe(self, topic: str, callback: SubscriberCallback) -> None:
        """Remove a callback from a topic."""
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(callback)
                if not self._subscribers[topic]:
                    del self._subscribers[topic]
                logger.debug(f"Unsubscribed from topic: {topic}")
            except ValueError:
                pass

    async def publish(self, topic: str, data: Dict[str, Any]) -> None:
        """
        Publish a message to a topic.

        - Notifies all matching subscribers (sync and async)
        - Stores in history (max 500)
        - Publishes to Redis if available
        """
        message = {
            "topic": topic,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
            "id": f"{topic}:{time.time_ns()}",
        }

        # Store in history
        self._history.append(message)
        if len(self._history) > self._MAX_HISTORY:
            self._history = self._history[-self._MAX_HISTORY:]

        # Notify matching subscribers
        await self._notify_subscribers(topic, data)

        # Publish to Redis (fire-and-forget)
        asyncio.create_task(self._publish_redis(topic, message))

    def get_history(
        self,
        topic: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve message history, optionally filtered by topic.

        Args:
            topic: Optional topic filter (supports wildcards)
            limit: Maximum number of messages to return (default 50)
        """
        if topic is None:
            return self._history[-limit:]

        filtered = [
            msg for msg in self._history
            if self._matches(topic, msg.get("topic", ""))
        ]
        return filtered[-limit:]

    # ------------------------------------------------------------------
    # Private Methods
    # ------------------------------------------------------------------

    def _matches(self, pattern: str, topic: str) -> bool:
        """
        Check if a topic matches a subscription pattern.

        Supports:
        - Exact match: "agent.coder.completed" matches "agent.coder.completed"
        - Star wildcard: "agent.*.completed" matches "agent.coder.completed"
        - Prefix wildcard: "agent.*" matches "agent.coder.completed"
        """
        if pattern == topic:
            return True

        # Handle prefix.* pattern (matches any subtopic)
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return topic.startswith(prefix + ".") or topic == prefix

        # Use fnmatch for glob-style wildcards
        return fnmatch.fnmatch(topic, pattern)

    async def _notify_subscribers(self, topic: str, data: Dict[str, Any]) -> None:
        """Notify all subscribers whose patterns match the given topic."""
        for pattern, callbacks in list(self._subscribers.items()):
            if self._matches(pattern, topic):
                for callback in callbacks:
                    try:
                        result = callback(topic, data)
                        if asyncio.iscoroutine(result):
                            await result
                    except Exception as e:
                        logger.error(
                            f"Subscriber error for topic '{topic}' "
                            f"(pattern '{pattern}'): {e}"
                        )

    async def _publish_redis(self, topic: str, message: Dict[str, Any]) -> None:
        """Publish message to Redis for distributed subscribers."""
        try:
            import json

            from config import settings

            # Lazy import redis
            import redis.asyncio as aioredis

            client = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
            async with client:
                await client.publish(
                    f"milyfe:bus:{topic}",
                    json.dumps(message, default=str),
                )
        except ImportError:
            # Redis not installed, skip
            pass
        except Exception as e:
            # Non-fatal — Redis is optional
            logger.debug(f"Redis publish skipped: {e}")
