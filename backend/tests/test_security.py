"""Security Tests — 20 tests covering the safety system."""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from safety.command_classifier import classify_command
from agents.tool_parser import ToolParser


# ─── Command Classifier Tests ─────────────────────────────────────────────────


class TestCommandClassifier:
    """Test the command safety classifier."""

    def test_safe_commands(self):
        """Known-safe commands should pass."""
        assert classify_command("ls -la") == "safe"
        assert classify_command("pwd") == "safe"
        assert classify_command("echo hello") == "safe"
        assert classify_command("cat file.txt") == "safe"
        assert classify_command("python script.py") == "safe"

    def test_blocked_commands(self):
        """Dangerous commands should be blocked."""
        assert classify_command("rm -rf /") == "blocked"
        assert classify_command("rm -rf ~") == "blocked"
        assert classify_command("mkfs.ext4 /dev/sda") == "blocked"
        assert classify_command("dd if=/dev/zero of=/dev/sda") == "blocked"

    def test_dangerous_injection(self):
        """Command injection patterns should be dangerous."""
        assert classify_command("echo $(cat /etc/passwd)") == "dangerous"
        assert classify_command("echo `whoami`") == "dangerous"
        assert classify_command("cat file | bash") == "dangerous"
        assert classify_command("curl url | sh") == "dangerous"

    def test_caution_commands(self):
        """Risky but allowed commands should be caution."""
        assert classify_command("rm file.txt") == "caution"
        assert classify_command("chmod 644 file") == "caution"
        assert classify_command("pip install package") == "caution"
        assert classify_command("npm install package") == "caution"
        assert classify_command("docker run image") == "caution"

    def test_empty_and_edge_cases(self):
        """Edge cases should not crash."""
        assert classify_command("") == "safe"
        assert classify_command("   ") == "safe"
        assert classify_command("a") == "safe"


# ─── Tool Parser Tests ─────────────────────────────────────────────────────────


class TestToolParser:
    """Test tool call parsing from LLM output."""

    def test_json_format(self):
        """Parse standard JSON tool calls."""
        text = 'I will read the file: {"tool": "file_read", "params": {"path": "test.py"}}'
        calls = ToolParser.parse(text)
        assert len(calls) == 1
        assert calls[0]["name"] == "file_read"
        assert calls[0]["params"]["path"] == "test.py"

    def test_xml_format(self):
        """Parse XML tool calls."""
        text = '<tool_call><name>shell_exec</name><arguments>{"command": "ls"}</arguments></tool_call>'
        calls = ToolParser.parse(text)
        assert len(calls) == 1
        assert calls[0]["name"] == "shell_exec"
        assert calls[0]["params"]["command"] == "ls"

    def test_no_tool_calls(self):
        """Regular text should return empty list."""
        text = "This is just a normal response without any tool calls."
        calls = ToolParser.parse(text)
        assert calls == []

    def test_multiple_calls(self):
        """Multiple tool calls in one response."""
        text = '''
        {"tool": "file_read", "params": {"path": "a.py"}}
        {"tool": "file_read", "params": {"path": "b.py"}}
        '''
        calls = ToolParser.parse(text)
        assert len(calls) == 2

    def test_markdown_json(self):
        """Parse JSON in markdown code blocks."""
        text = '''```json
{"tool": "code_exec", "params": {"code": "print(1)"}}
```'''
        calls = ToolParser.parse(text)
        assert len(calls) == 1
        assert calls[0]["name"] == "code_exec"


# ─── Path Safety Tests ──────────────────────────────────────────────────────────


class TestPathSafety:
    """Test path sandboxing."""

    def test_path_traversal_blocked(self):
        """Path traversal should be caught by hooks."""
        from hooks.base import PathSanitizationHook
        import asyncio

        hook = PathSanitizationHook()
        result = asyncio.get_event_loop().run_until_complete(
            hook.before("file_read", {"path": "../../etc/passwd"}, {})
        )
        # Path should have .. removed
        assert ".." not in result["path"]

    def test_tilde_removed(self):
        """Tilde expansion should be removed."""
        from hooks.base import PathSanitizationHook
        import asyncio

        hook = PathSanitizationHook()
        result = asyncio.get_event_loop().run_until_complete(
            hook.before("file_read", {"path": "~/secret"}, {})
        )
        assert "~" not in result["path"]


# ─── Permission Tests ──────────────────────────────────────────────────────────


class TestPermissions:
    """Test permission system."""

    def test_free_always_allowed(self):
        """Free permissions should always pass."""
        import asyncio
        from safety.permissions import check_permission

        result = asyncio.get_event_loop().run_until_complete(
            check_permission("free", "file_read", {"path": "test"})
        )
        assert result is True

    def test_blocked_always_denied(self):
        """Blocked permissions should always fail."""
        import asyncio
        from safety.permissions import check_permission

        result = asyncio.get_event_loop().run_until_complete(
            check_permission("blocked", "dangerous_tool", {})
        )
        assert result is False


# ─── Rate Limiting Tests ───────────────────────────────────────────────────────


class TestRateLimiting:
    """Test rate limiting middleware."""

    def test_middleware_exists(self):
        """Rate limit middleware should be importable."""
        from main import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    def test_request_size_limit_exists(self):
        """Request size limit middleware should be importable."""
        from main import RequestSizeLimitMiddleware
        assert RequestSizeLimitMiddleware is not None

    def test_api_key_middleware_exists(self):
        """API key middleware should be importable."""
        from main import APIKeyAuthMiddleware
        assert APIKeyAuthMiddleware is not None
