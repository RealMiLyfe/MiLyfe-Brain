"""
MiLyfe Brain - Search Tools

File glob search and content grep with context.
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import List, TYPE_CHECKING

from config import settings
from models.schemas import PermissionLevel

if TYPE_CHECKING:
    from tools.registry import ToolRegistry

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv", "dist", "build"}


def _resolve_search_path(path: str) -> Path:
    """Resolve a search path within workspace."""
    workspace = settings.workspace_path
    if path:
        resolved = (workspace / path).resolve()
        if not str(resolved).startswith(str(workspace)):
            raise PermissionError("Path resolves outside workspace")
        return resolved
    return workspace


def glob_search(pattern: str, path: str = "") -> str:
    """Search for files matching a glob pattern.

    Args:
        pattern: Glob/fnmatch pattern (e.g., '*.py', 'src/**/*.ts').
        path: Base directory to search from (relative to workspace).

    Returns:
        List of matching file paths (max 100 results).
    """
    base = _resolve_search_path(path)
    if not base.is_dir():
        return f"Error: Not a directory: {path}"

    workspace = settings.workspace_path
    matches: List[str] = []

    for root, dirs, files in os.walk(base):
        # Skip unwanted directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for filename in files:
            if fnmatch.fnmatch(filename, pattern):
                full_path = Path(root) / filename
                try:
                    rel_path = full_path.relative_to(workspace)
                    matches.append(str(rel_path))
                except ValueError:
                    matches.append(str(full_path))

            if len(matches) >= 100:
                break
        if len(matches) >= 100:
            break

    if not matches:
        return f"No files matching '{pattern}' found"

    result = f"Found {len(matches)} file(s) matching '{pattern}':\n"
    result += "\n".join(f"  {m}" for m in sorted(matches))
    if len(matches) >= 100:
        result += "\n  ... (results capped at 100)"
    return result


def grep_search(
    pattern: str,
    path: str = "",
    case_sensitive: bool = False,
    context_lines: int = 2,
    max_results: int = 50,
) -> str:
    """Search file contents using regex pattern.

    Args:
        pattern: Regex pattern to search for.
        path: Base directory to search from (relative to workspace).
        case_sensitive: Whether search is case sensitive.
        context_lines: Number of context lines before/after match.
        max_results: Maximum number of matches to return.

    Returns:
        Formatted search results with file paths, line numbers, and context.
    """
    base = _resolve_search_path(path)
    if not base.is_dir():
        return f"Error: Not a directory: {path}"

    workspace = settings.workspace_path

    try:
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"Invalid regex pattern: {e}"

    results: List[str] = []
    files_searched = 0
    max_results = min(max(max_results, 1), 200)

    # Text file extensions we search
    text_extensions = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss",
        ".json", ".yaml", ".yml", ".toml", ".md", ".txt", ".sh", ".bash",
        ".env", ".cfg", ".ini", ".conf", ".xml", ".sql", ".rs", ".go",
        ".java", ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift",
        ".kt", ".scala", ".r", ".lua", ".vim", ".dockerfile", ".makefile",
    }

    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for filename in files:
            # Only search text-like files
            ext = Path(filename).suffix.lower()
            if ext not in text_extensions and not filename.startswith("."):
                continue

            filepath = Path(root) / filename
            files_searched += 1

            try:
                lines = filepath.read_text(encoding="utf-8", errors="ignore").splitlines()
            except (OSError, UnicodeDecodeError):
                continue

            for i, line in enumerate(lines):
                if regex.search(line):
                    try:
                        rel_path = filepath.relative_to(workspace)
                    except ValueError:
                        rel_path = filepath

                    # Build context
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    context = []
                    for j in range(start, end):
                        marker = ">" if j == i else " "
                        context.append(f"  {marker} {j + 1:4d} | {lines[j]}")

                    results.append(f"{rel_path}:{i + 1}\n" + "\n".join(context))

                    if len(results) >= max_results:
                        break

            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break

    if not results:
        return f"No matches for /{pattern}/ in {files_searched} files searched"

    header = f"Found {len(results)} match(es) for /{pattern}/ ({files_searched} files searched):\n"
    body = "\n\n".join(results)
    if len(results) >= max_results:
        body += f"\n\n... (results capped at {max_results})"
    return header + "\n" + body


def register_search_tools(registry: ToolRegistry) -> None:
    """Register search tools with the tool registry."""
    registry.register(
        name="glob_search",
        handler=glob_search,
        category="search",
        description="Search for files matching a glob pattern within the workspace.",
        parameters={
            "pattern": {"type": "string", "description": "Glob/fnmatch pattern (e.g., '*.py')", "required": True},
            "path": {"type": "string", "description": "Base directory relative to workspace", "default": ""},
        },
        permission=PermissionLevel.SAFE,
        returns="List of matching file paths",
    )
    registry.register(
        name="grep_search",
        handler=grep_search,
        category="search",
        description="Search file contents using regex pattern with context lines.",
        parameters={
            "pattern": {"type": "string", "description": "Regex pattern to search for", "required": True},
            "path": {"type": "string", "description": "Base directory relative to workspace", "default": ""},
            "case_sensitive": {"type": "boolean", "description": "Case-sensitive search", "default": False},
            "context_lines": {"type": "integer", "description": "Context lines around match", "default": 2},
            "max_results": {"type": "integer", "description": "Max results to return", "default": 50},
        },
        permission=PermissionLevel.SAFE,
        returns="Formatted search results with context",
    )
