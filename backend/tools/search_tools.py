"""MiLyfe Brain — Glob + Grep Search Tools (first-class search)."""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path

from config import settings
from models.schemas import PermissionLevel

# Directories to always skip
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv", "dist", "build"}


async def glob_search(pattern: str, path: str = "") -> str:
    """Find files by glob pattern (e.g., '**/*.py', 'src/**/test_*.ts')."""
    workspace = Path(settings.workspace_dir)
    search_root = workspace / path if path else workspace

    if not search_root.exists():
        return f"Directory not found: {path or '.'}"

    matches = []
    for item in search_root.rglob("*"):
        # Skip excluded directories
        rel = item.relative_to(search_root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue

        if fnmatch.fnmatch(str(rel), pattern) or fnmatch.fnmatch(item.name, pattern):
            size = item.stat().st_size if item.is_file() else 0
            entry = f"{'D' if item.is_dir() else 'F'} {rel}"
            if item.is_file():
                entry += f" ({size}B)"
            matches.append(entry)

        if len(matches) >= 100:
            matches.append("...[truncated at 100 results]...")
            break

    return "\n".join(matches) if matches else f"No matches for: {pattern}"


async def grep_search(
    pattern: str,
    path: str = "",
    case_sensitive: bool = False,
    context_lines: int = 2,
    max_results: int = 50,
) -> str:
    """Regex content search with context lines."""
    workspace = Path(settings.workspace_dir)
    search_root = workspace / path if path else workspace

    if not search_root.exists():
        return f"Directory not found: {path or '.'}"

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"Invalid regex: {e}"

    results = []
    files_searched = 0

    for file_path in search_root.rglob("*"):
        if not file_path.is_file():
            continue

        rel = file_path.relative_to(search_root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue

        # Skip binary files
        if file_path.suffix in (".pyc", ".png", ".jpg", ".gif", ".ico", ".woff", ".ttf", ".zip", ".tar", ".gz"):
            continue

        files_searched += 1
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            for i, line in enumerate(lines):
                if regex.search(line):
                    # Add context
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    context = "\n".join(
                        f"  {'>' if j == i else ' '} {j+1}: {lines[j]}"
                        for j in range(start, end)
                    )
                    results.append(f"{rel}:{i+1}\n{context}")

                    if len(results) >= max_results:
                        break

        except (UnicodeDecodeError, PermissionError, OSError):
            continue

        if len(results) >= max_results:
            results.append(f"...[truncated at {max_results} results, searched {files_searched} files]...")
            break

    if not results:
        return f"No matches for /{pattern}/ in {files_searched} files"

    return "\n\n".join(results)


def register_search_tools(registry):
    """Register search tools."""
    registry.register(
        name="glob_search",
        handler=glob_search,
        category="Search",
        description="Find files by path pattern (e.g., **/*.py)",
        parameters={"pattern": "str (glob)", "path": "str (relative search root)"},
        permission=PermissionLevel.FREE,
    )
    registry.register(
        name="grep_search",
        handler=grep_search,
        category="Search",
        description="Regex content search with context lines",
        parameters={
            "pattern": "str (regex)",
            "path": "str",
            "case_sensitive": "bool",
            "context_lines": "int",
            "max_results": "int",
        },
        permission=PermissionLevel.FREE,
    )
