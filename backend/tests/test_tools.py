"""MiLyfe Brain — Tool System Tests."""

import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

# Patch workspace dir for tests
TEST_WORKSPACE = tempfile.mkdtemp()


@pytest.fixture(autouse=True)
def patch_workspace():
    with patch("config.settings.workspace_dir", TEST_WORKSPACE):
        yield


class TestFileTools:
    """Test file_read, file_write, file_delete, file_list."""

    @pytest.mark.asyncio
    async def test_file_write_and_read(self):
        from tools.file_tools import file_write, file_read
        result = await file_write(path="test_output.txt", content="hello world")
        assert "Written" in result
        content = await file_read(path="test_output.txt")
        assert content == "hello world"

    @pytest.mark.asyncio
    async def test_file_write_creates_dirs(self):
        from tools.file_tools import file_write, file_read
        await file_write(path="deep/nested/dir/file.txt", content="nested content")
        content = await file_read(path="deep/nested/dir/file.txt")
        assert content == "nested content"

    @pytest.mark.asyncio
    async def test_file_delete(self):
        from tools.file_tools import file_write, file_delete, file_read
        await file_write(path="to_delete.txt", content="bye")
        result = await file_delete(path="to_delete.txt")
        assert "Deleted" in result
        with pytest.raises(FileNotFoundError):
            await file_read(path="to_delete.txt")

    @pytest.mark.asyncio
    async def test_file_list(self):
        from tools.file_tools import file_write, file_list
        await file_write(path="list_test/a.txt", content="a")
        await file_write(path="list_test/b.txt", content="b")
        result = await file_list(path="list_test")
        assert "a.txt" in result
        assert "b.txt" in result

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self):
        from tools.file_tools import file_read
        with pytest.raises(PermissionError):
            await file_read(path="../../etc/passwd")

    @pytest.mark.asyncio
    async def test_read_nonexistent(self):
        from tools.file_tools import file_read
        with pytest.raises(FileNotFoundError):
            await file_read(path="does_not_exist.xyz")


class TestSearchTools:
    """Test glob_search and grep_search."""

    @pytest.mark.asyncio
    async def test_glob_search(self):
        from tools.file_tools import file_write
        from tools.search_tools import glob_search
        await file_write(path="search_test/module.py", content="import os")
        await file_write(path="search_test/data.json", content="{}")
        result = await glob_search(pattern="*.py", path="search_test")
        assert "module.py" in result

    @pytest.mark.asyncio
    async def test_grep_search(self):
        from tools.file_tools import file_write
        from tools.search_tools import grep_search
        await file_write(path="grep_test/code.py", content="def hello_world():\n    return 42\n")
        result = await grep_search(pattern="hello_world", path="grep_test")
        assert "hello_world" in result
        assert "code.py" in result

    @pytest.mark.asyncio
    async def test_grep_no_match(self):
        from tools.file_tools import file_write
        from tools.search_tools import grep_search
        await file_write(path="grep_test2/empty.py", content="x = 1")
        result = await grep_search(pattern="nonexistent_pattern_xyz", path="grep_test2")
        assert "No matches" in result


class TestCodeTools:
    """Test sandboxed code execution."""

    @pytest.mark.asyncio
    async def test_code_exec_simple(self):
        from tools.code_tools import code_exec
        result = await code_exec(code="print(2 + 2)")
        assert "4" in result

    @pytest.mark.asyncio
    async def test_code_exec_error(self):
        from tools.code_tools import code_exec
        result = await code_exec(code="raise ValueError('test error')")
        assert "ValueError" in result
        assert "test error" in result

    @pytest.mark.asyncio
    async def test_code_exec_no_output(self):
        from tools.code_tools import code_exec
        result = await code_exec(code="x = 42")
        assert result  # Should return something (even "(no output)")


class TestReplTools:
    """Test persistent REPL sessions."""

    @pytest.mark.asyncio
    async def test_repl_persistence(self):
        from tools.repl_tools import repl_execute, repl_variables
        await repl_execute(code="x = 42", session_id="test_session")
        result = await repl_execute(code="print(x * 2)", session_id="test_session")
        assert "84" in result

    @pytest.mark.asyncio
    async def test_repl_variables_list(self):
        from tools.repl_tools import repl_execute, repl_variables
        await repl_execute(code="name = 'brain'", session_id="var_test")
        result = await repl_variables(session_id="var_test")
        assert "name" in result

    @pytest.mark.asyncio
    async def test_repl_isolation(self):
        from tools.repl_tools import repl_execute
        await repl_execute(code="secret = 'abc'", session_id="session_a")
        result = await repl_execute(code="print(secret)", session_id="session_b")
        assert "NameError" in result or "not defined" in result


class TestScratchpadTools:
    """Test working memory scratchpad."""

    @pytest.mark.asyncio
    async def test_scratchpad_write_read(self):
        from tools.scratchpad_tools import scratchpad_write, scratchpad_read
        await scratchpad_write(content="remember this", category="note", session_id="sp_test")
        result = await scratchpad_read(session_id="sp_test")
        assert "remember this" in result

    @pytest.mark.asyncio
    async def test_scratchpad_category_filter(self):
        from tools.scratchpad_tools import scratchpad_write, scratchpad_read
        await scratchpad_write(content="task 1", category="todo", session_id="sp_filter")
        await scratchpad_write(content="found something", category="finding", session_id="sp_filter")
        result = await scratchpad_read(category="todo", session_id="sp_filter")
        assert "task 1" in result
        assert "found something" not in result

    @pytest.mark.asyncio
    async def test_scratchpad_invalid_category(self):
        from tools.scratchpad_tools import scratchpad_write
        result = await scratchpad_write(content="x", category="invalid_cat", session_id="sp_inv")
        assert "Invalid" in result
