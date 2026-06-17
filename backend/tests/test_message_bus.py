"""Unit tests for the inter-agent message bus."""

import pytest
from agents.message_bus import MessageBus, Topic, Message


@pytest.fixture
def bus():
    return MessageBus(max_history=100)



class TestPublish:
    """Test message publishing."""

    @pytest.mark.asyncio
    async def test_publish_returns_message(self, bus):
        msg = await bus.publish(Topic.TASK_COMPLETE, {"result": "done"}, sender_id="agent-1")
        assert isinstance(msg, Message)
        assert msg.topic == Topic.TASK_COMPLETE
        assert msg.payload["result"] == "done"
        assert msg.sender_id == "agent-1"

    @pytest.mark.asyncio
    async def test_publish_adds_to_history(self, bus):
        await bus.publish(Topic.STATUS_UPDATE, {"status": "running"})
        history = bus.get_history()
        assert len(history) == 1

    @pytest.mark.asyncio
    async def test_history_capped(self, bus):
        bus._max_history = 5
        for i in range(10):
            await bus.publish(Topic.STATUS_UPDATE, {"i": i})
        history = bus.get_history()
        assert len(history) == 5


class TestSubscribe:
    """Test subscriptions and delivery."""

    @pytest.mark.asyncio
    async def test_subscriber_receives_message(self, bus):
        received = []

        async def callback(msg: Message):
            received.append(msg)

        bus.subscribe(Topic.TASK_COMPLETE, callback, subscriber_id="sub-1")
        await bus.publish(Topic.TASK_COMPLETE, {"data": "hello"})

        assert len(received) == 1
        assert received[0].payload["data"] == "hello"

    @pytest.mark.asyncio
    async def test_wildcard_subscriber(self, bus):
        received = []

        async def callback(msg: Message):
            received.append(msg)

        bus.subscribe("*", callback, subscriber_id="wildcard")
        await bus.publish(Topic.TASK_COMPLETE, {"a": 1})
        await bus.publish(Topic.ERROR, {"b": 2})

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        received = []

        async def callback(msg: Message):
            received.append(msg)

        sub_id = bus.subscribe(Topic.STATUS_UPDATE, callback)
        await bus.publish(Topic.STATUS_UPDATE, {"x": 1})
        assert len(received) == 1

        bus.unsubscribe(sub_id)
        await bus.publish(Topic.STATUS_UPDATE, {"x": 2})
        assert len(received) == 1  # No new delivery

    @pytest.mark.asyncio
    async def test_unsubscribe_all(self, bus):
        async def cb(msg): pass

        bus.subscribe(Topic.TASK_COMPLETE, cb, subscriber_id="agent-x")
        bus.subscribe(Topic.ERROR, cb, subscriber_id="agent-x")
        bus.subscribe(Topic.HELP_NEEDED, cb, subscriber_id="other")

        count = bus.unsubscribe_all("agent-x")
        assert count == 2
        assert bus.subscriber_count == 1


class TestHistory:
    """Test history retrieval."""

    @pytest.mark.asyncio
    async def test_filter_by_topic(self, bus):
        await bus.publish(Topic.TASK_COMPLETE, {"a": 1})
        await bus.publish(Topic.ERROR, {"b": 2})
        await bus.publish(Topic.TASK_COMPLETE, {"c": 3})

        history = bus.get_history(topic=Topic.TASK_COMPLETE)
        assert len(history) == 2

    @pytest.mark.asyncio
    async def test_limit(self, bus):
        for i in range(10):
            await bus.publish(Topic.STATUS_UPDATE, {"i": i})
        history = bus.get_history(limit=3)
        assert len(history) == 3


class TestProperties:
    """Test bus properties."""

    def test_subscriber_count(self, bus):
        async def cb(msg): pass
        bus.subscribe(Topic.TASK_COMPLETE, cb)
        bus.subscribe(Topic.ERROR, cb)
        assert bus.subscriber_count == 2

    def test_topics(self, bus):
        async def cb(msg): pass
        bus.subscribe(Topic.TASK_COMPLETE, cb)
        bus.subscribe(Topic.ERROR, cb)
        assert Topic.TASK_COMPLETE in bus.topics
        assert Topic.ERROR in bus.topics
