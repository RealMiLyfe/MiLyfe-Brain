"""MiLyfe Brain Tool System — exposes all tools and the central registry."""

from backend.tools.registry import ToolRegistry, tool_registry
from backend.tools.file_tools import file_read, file_write, file_delete, file_list
from backend.tools.shell_tools import shell_exec
from backend.tools.code_tools import code_exec
from backend.tools.browser_tools import web_browse, web_search
from backend.tools.search_tools import glob_search, grep_search
from backend.tools.batch_tools import batch_execute
from backend.tools.repl_tools import repl_execute, repl_inspect, repl_variables
from backend.tools.scratchpad_tools import scratchpad_write, scratchpad_read, scratchpad_update
from backend.tools.llm_client import llm_generate


def register_all_tools() -> None:
    """Register every built-in tool with the global tool registry."""

    # ─── File Tools (free) ────────────────────────────────────────────
    tool_registry.register(
        name="file_read",
        func=file_read,
        description="Read the contents of a file at the given path.",
        parameters={
            "path": {"type": "string", "description": "Relative or absolute file path", "required": True},
        },
        permission="free",
    )
    tool_registry.register(
        name="file_write",
        func=file_write,
        description="Write content to a file, creating it if it doesn't exist.",
        parameters={
            "path": {"type": "string", "description": "Relative or absolute file path", "required": True},
            "content": {"type": "string", "description": "Content to write", "required": True},
        },
        permission="notify",
    )
    tool_registry.register(
        name="file_delete",
        func=file_delete,
        description="Delete a file at the given path.",
        parameters={
            "path": {"type": "string", "description": "File path to delete", "required": True},
        },
        permission="approve",
    )
    tool_registry.register(
        name="file_list",
        func=file_list,
        description="List files and directories at a path.",
        parameters={
            "path": {"type": "string", "description": "Directory path to list", "required": True},
            "recursive": {"type": "boolean", "description": "List recursively", "required": False},
        },
        permission="free",
    )

    # ─── Shell Tools (approve) ────────────────────────────────────────
    tool_registry.register(
        name="shell_exec",
        func=shell_exec,
        description="Execute a shell command and return stdout/stderr.",
        parameters={
            "command": {"type": "string", "description": "Shell command to execute", "required": True},
            "cwd": {"type": "string", "description": "Working directory", "required": False},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)", "required": False},
        },
        permission="approve",
    )

    # ─── Code Tools (notify) ─────────────────────────────────────────
    tool_registry.register(
        name="code_exec",
        func=code_exec,
        description="Execute sandboxed Python code and return the output.",
        parameters={
            "code": {"type": "string", "description": "Python code to execute", "required": True},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 10)", "required": False},
        },
        permission="notify",
    )

    # ─── Browser Tools (approve) ──────────────────────────────────────
    tool_registry.register(
        name="web_browse",
        func=web_browse,
        description="Browse a URL and return page content.",
        parameters={
            "url": {"type": "string", "description": "URL to browse", "required": True},
            "action": {"type": "string", "description": "Action: get, click, type, scroll", "required": False},
        },
        permission="approve",
    )
    tool_registry.register(
        name="web_search",
        func=web_search,
        description="Search the web and return results.",
        parameters={
            "query": {"type": "string", "description": "Search query", "required": True},
        },
        permission="approve",
    )

    # ─── Search Tools (free) ─────────────────────────────────────────
    tool_registry.register(
        name="glob_search",
        func=glob_search,
        description="Search for files matching a glob pattern.",
        parameters={
            "pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)", "required": True},
            "root": {"type": "string", "description": "Root directory to search from", "required": False},
        },
        permission="free",
    )
    tool_registry.register(
        name="grep_search",
        func=grep_search,
        description="Search file contents using regex pattern.",
        parameters={
            "pattern": {"type": "string", "description": "Regex pattern to search for", "required": True},
            "path": {"type": "string", "description": "File or directory to search in", "required": False},
            "context_lines": {"type": "integer", "description": "Lines of context around matches", "required": False},
        },
        permission="free",
    )

    # ─── Batch Tools (notify) ────────────────────────────────────────
    tool_registry.register(
        name="batch_execute",
        func=batch_execute,
        description="Execute multiple tool calls in parallel.",
        parameters={
            "calls": {
                "type": "array",
                "description": "List of {tool, arguments} dicts to execute",
                "required": True,
            },
        },
        permission="notify",
    )

    # ─── REPL Tools (free) ───────────────────────────────────────────
    tool_registry.register(
        name="repl_execute",
        func=repl_execute,
        description="Execute code in a persistent Python REPL session.",
        parameters={
            "code": {"type": "string", "description": "Python code to execute", "required": True},
            "session_id": {"type": "string", "description": "Session identifier", "required": False},
        },
        permission="free",
    )
    tool_registry.register(
        name="repl_inspect",
        func=repl_inspect,
        description="Inspect a variable in the REPL session.",
        parameters={
            "variable": {"type": "string", "description": "Variable name to inspect", "required": True},
            "session_id": {"type": "string", "description": "Session identifier", "required": False},
        },
        permission="free",
    )
    tool_registry.register(
        name="repl_variables",
        func=repl_variables,
        description="List all variables in the REPL session.",
        parameters={
            "session_id": {"type": "string", "description": "Session identifier", "required": False},
        },
        permission="free",
    )

    # ─── Scratchpad Tools (free) ─────────────────────────────────────
    tool_registry.register(
        name="scratchpad_write",
        func=scratchpad_write,
        description="Write a value to the agent scratchpad.",
        parameters={
            "key": {"type": "string", "description": "Key to store under", "required": True},
            "value": {"type": "string", "description": "Value to store", "required": True},
            "category": {"type": "string", "description": "Category tag", "required": False},
        },
        permission="free",
    )
    tool_registry.register(
        name="scratchpad_read",
        func=scratchpad_read,
        description="Read from the agent scratchpad.",
        parameters={
            "key": {"type": "string", "description": "Key to read (omit for all entries)", "required": False},
        },
        permission="free",
    )
    tool_registry.register(
        name="scratchpad_update",
        func=scratchpad_update,
        description="Update an existing scratchpad entry.",
        parameters={
            "key": {"type": "string", "description": "Key to update", "required": True},
            "value": {"type": "string", "description": "New value", "required": True},
        },
        permission="free",
    )


__all__ = [
    "ToolRegistry",
    "tool_registry",
    "register_all_tools",
    "file_read",
    "file_write",
    "file_delete",
    "file_list",
    "shell_exec",
    "code_exec",
    "web_browse",
    "web_search",
    "glob_search",
    "grep_search",
    "batch_execute",
    "repl_execute",
    "repl_inspect",
    "repl_variables",
    "scratchpad_write",
    "scratchpad_read",
    "scratchpad_update",
    "llm_generate",
]
