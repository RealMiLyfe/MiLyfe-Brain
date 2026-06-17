"""
MiLyfe Brain - Tool Tests

Tests for file_tools, search_tools, code_tools, repl_tools, scratchpad_tools.
Uses pytest + pytest-asyncio with patched workspace directory.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest
import pytest_asyncio

# Ensure backend is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def workspace_dir():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def patched_settings(workspace_dir):
    """Patch settings.workspace_dir to use temp directory."""
    with patch("config.settings.workspace_dir", workspace_dir):
        with patch("config.settings.workspace_path", Path(workspace_dir)):
            yield workspace_dir


# ============================================================
# File Tools Tests
# ============================================================


class TestFileTools:
    """Tests for file_tools: write, read, delete, list."""

    @pytest.mark.asyncio
    async def test_write_file(self, patched_settings):
        """Test writing a file to the workspace."""
        from tools.file_tools import write_file

        result = await write_file(
            path="test.txt",
            content="Hello, World!",
        )

        assert result["success"] is True
        filepath = Path(patched_settings) / "test.txt"
        assert filepath.exists()
        assert filepath.read_text() == "Hello, World!"

    @pytest.mark.asyncio
    async def test_read_file(self, patched_settings):
        """Test reading a file from the workspace."""
        from tools.file_tools import read_file, write_file

        await write_file(path="read_test.txt", content="Read me!")
        result = await read_file(path="read_test.txt")

        assert result["success"] is True
        assert "Read me!" in result.get("content", "")

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, patched_settings):
        """Test reading a file that doesn't exist."""
        from tools.file_tools import read_file

        result = await read_file(path="nonexistent.txt")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_delete_file(self, patched_settings):
        """Test deleting a file."""
        from tools.file_tools import delete_file, write_file

        await write_file(path="to_delete.txt", content="Delete me")
        result = await delete_file(path="to_delete.txt")

        assert result["success"] is True
        filepath = Path(patched_settings) / "to_delete.txt"
        assert not filepath.exists()

    @pytest.mark.asyncio
    async def test_list_files(self, patched_settings):
        """Test listing files in workspace."""
        from tools.file_tools import list_files, write_file

        await write_file(path="file1.txt", content="one")
        await write_file(path="file2.txt", content="two")
        await write_file(path="subdir/file3.txt", content="three")

        result = await list_files(path=".")
        assert result["success"] is True
        entries = result.get("entries", [])
        names = [e["name"] for e in entries if isinstance(e, dict)]
        assert "file1.txt" in names or len(entries) >= 2

    @pytest.mark.asyncio
    async def test_write_creates_parent_dirs(self, patched_settings):
        """Test that writing to nested path creates parent directories."""
        from tools.file_tools import write_file

        result = await write_file(
            path="deep/nested/dir/file.txt",
            content="Nested content",
        )

        assert result["success"] is True
        filepath = Path(patched_settings) / "deep" / "nested" / "dir" / "file.txt"
        assert filepath.exists()


# ============================================================
# Search Tools Tests
# ============================================================


class TestSearchTools:
    """Tests for search_tools: glob and grep."""

    @pytest.mark.asyncio
    async def test_glob_search(self, patched_settings):
        """Test glob pattern file search."""
        from tools.file_tools import write_file
        from tools.search_tools import glob_search

        await write_file(path="src/main.py", content="print('hello')")
        await write_file(path="src/utils.py", content="def util(): pass")
        await write_file(path="tests/test_main.py", content="def test(): pass")

        result = await glob_search(pattern="**/*.py")
        assert result["success"] is True
        matches = result.get("matches", [])
        assert len(matches) >= 2

    @pytest.mark.asyncio
    async def test_grep_search(self, patched_settings):
        """Test grep content search."""
        from tools.file_tools import write_file
        from tools.search_tools import grep_search

        await write_file(path="code.py", content="def hello_world():\n    return 'hello'\n")
        await write_file(path="other.py", content="def goodbye():\n    return 'bye'\n")

        result = await grep_search(pattern="hello", path=".")
        assert result["success"] is True
        matches = result.get("matches", [])
        assert len(matches) >= 1

    @pytest.mark.asyncio
    async def test_grep_no_results(self, patched_settings):
        """Test grep with no matching results."""
        from tools.file_tools import write_file
        from tools.search_tools import grep_search

        await write_file(path="empty_search.txt", content="nothing special here")

        result = await grep_search(pattern="xyz_not_found_123", path=".")
        assert result["success"] is True
        matches = result.get("matches", [])
        assert len(matches) == 0


# ============================================================
# Code Tools Tests
# ============================================================


class TestCodeTools:
    """Tests for code_tools: exec."""

    @pytest.mark.asyncio
    async def test_exec_python(self, patched_settings):
        """Test executing Python code."""
        from tools.code_tools import exec_code

        result = await exec_code(
            code="print(2 + 2)",
            language="python",
        )

        assert result["success"] is True
        assert "4" in result.get("output", "")

    @pytest.mark.asyncio
    async def test_exec_python_with_error(self, patched_settings):
        """Test executing code that raises an error."""
        from tools.code_tools import exec_code

        result = await exec_code(
            code="raise ValueError('test error')",
            language="python",
        )

        assert result["success"] is False
        assert "error" in result.get("error", "").lower() or "ValueError" in result.get("output", "")

    @pytest.mark.asyncio
    async def test_exec_multiline(self, patched_settings):
        """Test executing multiline Python code."""
        from tools.code_tools import exec_code

        code = """
x = [1, 2, 3, 4, 5]
result = sum(x)
print(f"Sum: {result}")
"""
        result = await exec_code(code=code, language="python")
        assert result["success"] is True
        assert "Sum: 15" in result.get("output", "")


# ============================================================
# REPL Tools Tests
# ============================================================


class TestReplTools:
    """Tests for repl_tools: persistence across calls."""

    @pytest.mark.asyncio
    async def test_repl_persistence(self, patched_settings):
        """Test that REPL state persists across calls."""
        from tools.repl_tools import repl_exec

        # First call sets a variable
        result1 = await repl_exec(code="x = 42")
        assert result1["success"] is True

        # Second call uses the variable
        result2 = await repl_exec(code="print(x * 2)")
        assert result2["success"] is True
        assert "84" in result2.get("output", "")

    @pytest.mark.asyncio
    async def test_repl_import_persistence(self, patched_settings):
        """Test that imports persist in REPL."""
        from tools.repl_tools import repl_exec

        result1 = await repl_exec(code="import math")
        assert result1["success"] is True

        result2 = await repl_exec(code="print(math.pi)")
        assert result2["success"] is True
        assert "3.14" in result2.get("output", "")

    @pytest.mark.asyncio
    async def test_repl_function_persistence(self, patched_settings):
        """Test that function definitions persist."""
        from tools.repl_tools import repl_exec

        result1 = await repl_exec(code="def double(n): return n * 2")
        assert result1["success"] is True

        result2 = await repl_exec(code="print(double(21))")
        assert result2["success"] is True
        assert "42" in result2.get("output", "")


# ============================================================
# Scratchpad Tools Tests
# ============================================================


class TestScratchpadTools:
    """Tests for scratchpad_tools: write, read, categories."""

    @pytest.mark.asyncio
    async def test_write_and_read(self, patched_settings):
        """Test writing and reading a scratchpad entry."""
        from tools.scratchpad_tools import read_scratchpad, write_scratchpad

        write_result = await write_scratchpad(
            key="test_key",
            value="test_value",
            category="notes",
        )
        assert write_result["success"] is True

        read_result = await read_scratchpad(key="test_key")
        assert read_result["success"] is True
        assert read_result.get("value") == "test_value"

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, patched_settings):
        """Test reading a key that doesn't exist."""
        from tools.scratchpad_tools import read_scratchpad

        result = await read_scratchpad(key="nonexistent_key_xyz")
        assert result["success"] is False or result.get("value") is None

    @pytest.mark.asyncio
    async def test_overwrite_entry(self, patched_settings):
        """Test overwriting an existing scratchpad entry."""
        from tools.scratchpad_tools import read_scratchpad, write_scratchpad

        await write_scratchpad(key="overwrite_me", value="original", category="test")
        await write_scratchpad(key="overwrite_me", value="updated", category="test")

        result = await read_scratchpad(key="overwrite_me")
        assert result.get("value") == "updated"

    @pytest.mark.asyncio
    async def test_list_categories(self, patched_settings):
        """Test listing scratchpad categories."""
        from tools.scratchpad_tools import list_categories, write_scratchpad

        await write_scratchpad(key="a", value="1", category="alpha")
        await write_scratchpad(key="b", value="2", category="beta")

        result = await list_categories()
        assert result["success"] is True
        categories = result.get("categories", [])
        assert "alpha" in categories
        assert "beta" in categories
