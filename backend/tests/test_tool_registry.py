"""Unit tests for the tool registry."""

import pytest
import pytest_asyncio
from tools.registry import ToolRegistry, Permission


@pytest.fixture
def registry():
    """Fresh registry for each test."""
    return ToolRegistry()


@pytest.fixture
def registry_with_tools(registry):
    """Registry with sample tools registered."""

    async def mock_read(path: str) -> str:
        return f"Content of {path}"

    async def mock_write(path: str, content: str) -> str:
        return f"Written {len(content)} bytes to {path}"

    async def mock_delete(path: str) -> str:
        return f"Deleted {path}"

    async def mock_blocked() -> str:
        return "should never execute"

    registry.register("file_read", mock_read, "Read a file", {"path": {"type": "string"}}, "free")
    registry.register("file_write", mock_write, "Write a file", {"path": {"type": "string"}, "content": {"type": "string"}}, "notify")
    registry.register("file_delete", mock_delete, "Delete a file", {"path": {"type": "string"}}, "approve")
    registry.register("dangerous_op", mock_blocked, "Blocked op", {}, "blocked")

    return registry


class TestRegistration:
    """Test tool registration."""

    def test_register_tool(self, registry):
        async def handler(x: str) -> str:
            return x

        registry.register("test_tool", handler, "A test tool", {"x": {"type": "string"}}, "free")
        assert registry.has("test_tool")
        assert registry.count() == 1

    def test_register_multiple_tools(self, registry_with_tools):
        assert registry_with_tools.count() == 4

    def test_get_registered_tool(self, registry_with_tools):
        tool = registry_with_tools.get("file_read")
        assert tool is not None
        assert tool["name"] == "file_read"
        assert tool["permission"] == Permission.FREE

    def test_get_nonexistent_tool(self, registry_with_tools):
        assert registry_with_tools.get("nonexistent") is None

    def test_has_tool(self, registry_with_tools):
        assert registry_with_tools.has("file_read")
        assert not registry_with_tools.has("does_not_exist")

    def test_list_all(self, registry_with_tools):
        tools = registry_with_tools.list_all()
        assert len(tools) == 4
        names = {t["name"] for t in tools}
        assert "file_read" in names
        assert "file_delete" in names
        # Handler should not be exposed
        for t in tools:
            assert "handler" not in t


class TestExecution:
    """Test tool execution with permissions."""

    @pytest.mark.asyncio
    async def test_execute_free_tool(self, registry_with_tools):
        result = await registry_with_tools.execute("file_read", {"path": "test.txt"})
        assert result == "Content of test.txt"

    @pytest.mark.asyncio
    async def test_execute_notify_tool(self, registry_with_tools):
        result = await registry_with_tools.execute("file_write", {"path": "out.txt", "content": "hello"})
        assert "5 bytes" in result

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires live approval service with WebSocket; tested via integration tests")
    async def test_execute_approve_tool_denied(self, registry_with_tools):
        """Approve-level tools raise PermissionError when not pre-approved."""
        with pytest.raises(PermissionError):
            await registry_with_tools.execute("file_delete", {"path": "x.txt"}, approved=False)

    @pytest.mark.asyncio
    async def test_execute_approve_tool_with_approval(self, registry_with_tools):
        result = await registry_with_tools.execute("file_delete", {"path": "x.txt"}, approved=True)
        assert "Deleted x.txt" in result

    @pytest.mark.asyncio
    async def test_execute_blocked_tool(self, registry_with_tools):
        with pytest.raises(PermissionError, match="blocked"):
            await registry_with_tools.execute("dangerous_op", {})

    @pytest.mark.asyncio
    async def test_execute_nonexistent_tool(self, registry_with_tools):
        with pytest.raises(ValueError, match="not found"):
            await registry_with_tools.execute("nonexistent", {})


class TestHooks:
    """Test pre and post hooks."""

    @pytest.mark.asyncio
    async def test_pre_hook_called(self, registry_with_tools):
        hook_calls = []

        async def pre_hook(name, args):
            hook_calls.append(("pre", name, args))

        registry_with_tools.add_pre_hook(pre_hook)
        await registry_with_tools.execute("file_read", {"path": "test.txt"})

        assert len(hook_calls) == 1
        assert hook_calls[0][1] == "file_read"

    @pytest.mark.asyncio
    async def test_post_hook_called(self, registry_with_tools):
        hook_calls = []

        async def post_hook(name, data):
            hook_calls.append(("post", name, data))

        registry_with_tools.add_post_hook(post_hook)
        await registry_with_tools.execute("file_read", {"path": "test.txt"})

        assert len(hook_calls) == 1
        assert hook_calls[0][1] == "file_read"
        assert "result" in hook_calls[0][2]

    @pytest.mark.asyncio
    async def test_hook_failure_doesnt_block(self, registry_with_tools):
        async def bad_hook(name, args):
            raise RuntimeError("Hook exploded")

        registry_with_tools.add_pre_hook(bad_hook)
        # Should still execute successfully
        result = await registry_with_tools.execute("file_read", {"path": "test.txt"})
        assert "Content of test.txt" in result
