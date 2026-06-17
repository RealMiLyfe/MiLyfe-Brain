"""Inter-Agent Message Bus — Topic-based pub/sub messaging."""

import asyncio
from datetime import datetime
from typing import Any, Callable, Optional
from collections import defaultdict

import structlog

logger = structlog.get_logger()


class Message:
    """A message sent between agents."""

    def __init__(
        self,
        topic: str,
        sender_id: str,
        sender_role: str,
        content: Any,
        target_role: Optional[str] = None,
    ):
        self.topic = topic
        self.sender_id = sender_id
        self.sender_role = sender_role
        self.content = content
        self.target_role = target_role
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "sender_id": self.sender_id,
            "sender_role": self.sender_role,
            "content": self.content,
            "target_role": self.target_role,
            "timestamp": self.timestamp.isoformat(),
        }


class MessageBus:
    """Topic-based message bus for inter-agent communication."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._history: list[Message] = []
        self._max_history = 1000
        self._lock = asyncio.Lock()

    def subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe to messages on a topic."""
        self._subscribers[topic].append(callback)
        logger.debug("Subscription added", topic=topic)

    def unsubscribe(self, topic: str, callback: Callable) -> None:
        """Unsubscribe from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic] = [cb for cb in self._subscribers[topic] if cb != callback]

    async def publish(self, message: Message) -> None:
        """Publish a message to all subscribers of its topic."""
        async with self._lock:
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

        # Notify subscribers
        subscribers = self._subscribers.get(message.topic, [])
        wildcard_subscribers = self._subscribers.get("*", [])

        all_subscribers = subscribers + wildcard_subscribers

        for callback in all_subscribers:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error("Message handler error", topic=message.topic, error=str(e))

        logger.debug(
            "Message published",
            topic=message.topic,
            sender=message.sender_role,
            subscriber_count=len(all_subscribers),
        )

    async def send(
        self,
        topic: str,
        sender_id: str,
        sender_role: str,
        content: Any,
        target_role: Optional[str] = None,
    ) -> None:
        """Convenience method to create and publish a message."""
        message = Message(
            topic=topic,
            sender_id=sender_id,
            sender_role=sender_role,
            content=content,
            target_role=target_role,
        )
        await self.publish(message)

    def get_history(
        self,
        topic: Optional[str] = None,
        sender_role: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Get message history, optionally filtered."""
        messages = self._history

        if topic:
            messages = [m for m in messages if m.topic == topic]
        if sender_role:
            messages = [m for m in messages if m.sender_role == sender_role]

        return [m.to_dict() for m in messages[-limit:]]

    def clear_history(self) -> None:
        """Clear all message history."""
        self._history = []


# Global message bus instance
message_bus = MessageBus()
