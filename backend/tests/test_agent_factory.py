"""Unit tests for the agent factory and agent lifecycle."""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from agents.base import AgentRole, AgentStatus, BaseAgent
from agents.factory import AgentFactory
from agents.message_bus import get_message_bus, reset_message_bus


@pytest.fixture(autouse=True)
def reset_bus():
    """Reset message bus between tests."""
    reset_message_bus()
    yield
    reset_message_bus()


@pytest.fixture
def factory():
    """Fresh agent factory with mock tool executor."""
    async def mock_executor(name: str, args: dict) -> str:
        return f"Executed {name} with {args}"

    return AgentFactory(tool_executor=mock_executor, max_agents=5)


class TestSpawn:
    """Test agent spawning."""

    def test_spawn_by_string_role(self, factory):
        agent = factory.spawn(role="coder")
        assert agent.role == AgentRole.CODER
        assert agent.status == AgentStatus.IDLE

    def test_spawn_by_enum_role(self, factory):
        agent = factory.spawn(role=AgentRole.RESEARCHER)
        assert agent.role == AgentRole.RESEARCHER

    def test_spawn_all_roles(self, factory):
        # Increase limit for this test
        factory._max_agents = 20
        for role in AgentRole:
            agent = factory.spawn(role=role)
            assert agent.role == role

    def test_spawn_with_custom_name(self, factory):
        agent = factory.spawn(role="coder", name="my-coder")
        assert agent.name == "my-coder"

    def test_spawn_with_context(self, factory):
        agent = factory.spawn(role="coder", context={"playbook_id": "test-123"})
        assert agent.context["playbook_id"] == "test-123"

    def test_spawn_invalid_role(self, factory):
        with pytest.raises(ValueError, match="Unknown agent role"):
            factory.spawn(role="invalid_role")

    def test_spawn_exceeds_max_agents(self, factory):
        for i in range(5):
            factory.spawn(role="coder", name=f"coder-{i}")
        with pytest.raises(ValueError, match="Maximum active agents"):
            factory.spawn(role="coder")


class TestRetire:
    """Test agent retirement."""

    @pytest.mark.asyncio
    async def test_retire_agent(self, factory):
        agent = factory.spawn(role="coder")
        result = await factory.retire(agent.id)
        assert result is True
        assert factory.active_count == 0

    @pytest.mark.asyncio
    async def test_retire_nonexistent(self, factory):
        result = await factory.retire("nonexistent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_retire_all(self, factory):
        factory.spawn(role="coder")
        factory.spawn(role="researcher")
        factory.spawn(role="writer")
        count = await factory.retire_all()
        assert count == 3
        assert factory.active_count == 0


class TestLookup:
    """Test agent lookup and listing."""

    def test_get_by_id(self, factory):
        agent = factory.spawn(role="coder")
        found = factory.get(agent.id)
        assert found is not None
        assert found.id == agent.id

    def test_get_nonexistent(self, factory):
        assert factory.get("nope") is None

    def test_get_by_role(self, factory):
        factory.spawn(role="coder")
        factory.spawn(role="coder")
        factory.spawn(role="researcher")
        coders = factory.get_by_role("coder")
        assert len(coders) == 2

    def test_list_active(self, factory):
        factory.spawn(role="coder")
        factory.spawn(role="researcher")
        active = factory.list_active()
        assert len(active) == 2

    def test_capacity_remaining(self, factory):
        factory.spawn(role="coder")
        assert factory.capacity_remaining == 4


class TestCleanup:
    """Test stale agent cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_stale(self, factory):
        import time
        agent = factory.spawn(role="coder")
        # Simulate old last_active
        agent.last_active = time.time() - 700
        count = await factory.cleanup_stale(max_idle_seconds=600)
        assert count == 1

    @pytest.mark.asyncio
    async def test_dont_cleanup_active(self, factory):
        agent = factory.spawn(role="coder")
        agent.status = AgentStatus.THINKING
        import time
        agent.last_active = time.time() - 700
        count = await factory.cleanup_stale(max_idle_seconds=600)
        assert count == 0  # Thinking agents not cleaned


class TestToolExecutor:
    """Test tool executor wiring."""

    def test_executor_wired_on_spawn(self, factory):
        agent = factory.spawn(role="coder")
        assert hasattr(agent, "_tool_executor")

    def test_set_tool_executor_updates_existing(self, factory):
        agent = factory.spawn(role="coder")
        calls = []

        async def new_executor(name, args):
            calls.append(name)
            return "done"

        factory.set_tool_executor(new_executor)
        assert agent._tool_executor is new_executor
