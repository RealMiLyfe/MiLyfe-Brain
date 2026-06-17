"""Inter-agent message bus with topic-based pub/sub.

Provides asynchronous communication between agents using
topic-based publish/subscribe pattern.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class Topic(str, Enum):
    """Predefined message bus topics."""

    TASK_COMPLETE = "task_complete"
    HELP_NEEDED = "help_needed"
    REVIEW_REQUEST = "review_request"
    STATUS_UPDATE = "status_update"
    AGENT_SPAWNED = "agent_spawned"
    AGENT_RETIRED = "agent_retired"
    ERROR = "error"


@dataclass
class Message:
    """A message on the bus."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    sender_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# Type for subscriber callbacks
SubscriberCallback = Callable[[Message], Coroutine[Any, Any, None]]


@dataclass
class Subscription:
    """Represents a subscription to a topic."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: str = ""
    callback: Optional[SubscriberCallback] = None
    subscriber_id: str = ""


class MessageBus:
    """Topic-based pub/sub message bus for inter-agent communication.

    Thread-safe, async-first implementation supporting:
    - Multiple subscribers per topic
    - Wildcard subscriptions (subscribe to all topics)
    - Message history (configurable retention)
    - Dead letter handling for failed deliveries
    """

    def __init__(self, max_history: int = 1000) -> None:
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._wildcard_subscriptions: List[Subscription] = []
        self._history: List[Message] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()
        self._dead_letters: List[Message] = []

    async def publish(
        self,
        topic: str,
        payload: Dict[str, Any],
        sender_id: str = "",
    ) -> Message:
        """Publish a message to a topic.

        Args:
            topic: The topic to publish to (use Topic enum values).
            payload: Dictionary payload for the message.
            sender_id: ID of the sending agent.

        Returns:
            The published Message instance.
        """
        message = Message(
            topic=topic,
            sender_id=sender_id,
            payload=payload,
        )

        async with self._lock:
            self._history.append(message)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]

        # Get subscribers for this topic
        subscribers = self._subscriptions.get(topic, []).copy()
        subscribers.extend(self._wildcard_subscriptions)

        # Deliver to all subscribers
        delivery_tasks = []
        for sub in subscribers:
            if sub.callback is not None:
                delivery_tasks.append(self._deliver(sub, message))

        if delivery_tasks:
            results = await asyncio.gather(*delivery_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        "Failed to deliver message %s to subscriber %s: %s",
                        message.id,
                        subscribers[i].id,
                        result,
                    )
                    self._dead_letters.append(message)

        logger.debug(
            "Published message %s to topic '%s' (%d subscribers)",
            message.id,
            topic,
            len(subscribers),
        )

        return message

    async def _deliver(self, subscription: Subscription, message: Message) -> None:
        """Deliver a message to a single subscriber."""
        if subscription.callback is not None:
            await subscription.callback(message)

    def subscribe(
        self,
        topic: str,
        callback: SubscriberCallback,
        subscriber_id: str = "",
    ) -> str:
        """Subscribe to a topic.

        Args:
            topic: Topic to subscribe to. Use "*" for all topics.
            callback: Async function called when a message is published.
            subscriber_id: Optional ID of the subscribing agent.

        Returns:
            Subscription ID (for unsubscribing).
        """
        subscription = Subscription(
            topic=topic,
            callback=callback,
            subscriber_id=subscriber_id,
        )

        if topic == "*":
            self._wildcard_subscriptions.append(subscription)
        else:
            if topic not in self._subscriptions:
                self._subscriptions[topic] = []
            self._subscriptions[topic].append(subscription)

        logger.debug(
            "Subscriber %s subscribed to topic '%s' (sub_id=%s)",
            subscriber_id,
            topic,
            subscription.id,
        )

        return subscription.id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by its ID.

        Args:
            subscription_id: The subscription ID returned by subscribe().

        Returns:
            True if found and removed, False otherwise.
        """
        # Check topic subscriptions
        for topic, subs in self._subscriptions.items():
            for sub in subs:
                if sub.id == subscription_id:
                    subs.remove(sub)
                    logger.debug(
                        "Unsubscribed %s from topic '%s'", subscription_id, topic
                    )
                    return True

        # Check wildcard subscriptions
        for sub in self._wildcard_subscriptions:
            if sub.id == subscription_id:
                self._wildcard_subscriptions.remove(sub)
                logger.debug("Unsubscribed %s from wildcard", subscription_id)
                return True

        return False

    def unsubscribe_all(self, subscriber_id: str) -> int:
        """Remove all subscriptions for a given subscriber.

        Args:
            subscriber_id: The agent/subscriber ID.

        Returns:
            Number of subscriptions removed.
        """
        count = 0

        for topic in list(self._subscriptions.keys()):
            original_len = len(self._subscriptions[topic])
            self._subscriptions[topic] = [
                s
                for s in self._subscriptions[topic]
                if s.subscriber_id != subscriber_id
            ]
            count += original_len - len(self._subscriptions[topic])

        original_len = len(self._wildcard_subscriptions)
        self._wildcard_subscriptions = [
            s for s in self._wildcard_subscriptions if s.subscriber_id != subscriber_id
        ]
        count += original_len - len(self._wildcard_subscriptions)

        if count > 0:
            logger.debug(
                "Removed %d subscriptions for subscriber %s", count, subscriber_id
            )

        return count

    def get_history(
        self,
        topic: Optional[str] = None,
        limit: int = 50,
    ) -> List[Message]:
        """Get recent message history.

        Args:
            topic: Filter by topic. None for all messages.
            limit: Maximum messages to return.

        Returns:
            List of recent messages (newest last).
        """
        if topic:
            filtered = [m for m in self._history if m.topic == topic]
        else:
            filtered = self._history.copy()

        return filtered[-limit:]

    def get_dead_letters(self, limit: int = 50) -> List[Message]:
        """Get messages that failed delivery."""
        return self._dead_letters[-limit:]

    @property
    def subscriber_count(self) -> int:
        """Total number of active subscriptions."""
        total = len(self._wildcard_subscriptions)
        for subs in self._subscriptions.values():
            total += len(subs)
        return total

    @property
    def topics(self) -> Set[str]:
        """Set of topics that have subscribers."""
        return set(self._subscriptions.keys())


# Global singleton message bus instance
_message_bus: Optional[MessageBus] = None


def get_message_bus() -> MessageBus:
    """Get or create the global message bus singleton."""
    global _message_bus
    if _message_bus is None:
        _message_bus = MessageBus()
    return _message_bus


def reset_message_bus() -> None:
    """Reset the global message bus (useful for testing)."""
    global _message_bus
    _message_bus = None
