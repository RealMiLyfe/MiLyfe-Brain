"""Search Tools — Glob and Grep (first-class search primitives)."""

import os
import re
from pathlib import Path

from config import settings

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv", ".cache"}


async def glob_search(pattern: str, path: str = ".") -> str:
    """Find files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g., '**/*.py', 'src/**/test_*.ts')
        path: Base directory to search from
    """
    base = Path(settings.workspace_dir) / path if not os.path.isabs(path) else Path(path)

    if not base.exists():
        return f"Path not found: {path}"

    matches = []
    try:
        for match in base.glob(pattern):
            # Skip excluded directories
            parts = match.relative_to(base).parts
            if any(part in SKIP_DIRS for part in parts):
                continue
            rel_path = str(match.relative_to(base))
            file_type = "D" if match.is_dir() else "F"
            matches.append(f"[{file_type}] {rel_path}")

            if len(matches) >= 100:
                matches.append("...[truncated at 100 results]")
                break
    except Exception as e:
        return f"Glob error: {str(e)}"

    return "\n".join(matches) if matches else f"No matches for pattern: {pattern}"


async def grep_search(pattern: str, path: str = ".", context_lines: int = 2) -> str:
    """Search file contents with regex.

    Args:
        pattern: Regex pattern to search for
        path: Directory or file to search
        context_lines: Lines of context around matches
    """
    base = Path(settings.workspace_dir) / path if not os.path.isabs(path) else Path(path)

    if not base.exists():
        return f"Path not found: {path}"

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return f"Invalid regex: {str(e)}"

    results = []
    files_to_search = []

    if base.is_file():
        files_to_search = [base]
    else:
        for f in base.rglob("*"):
            if f.is_file():
                parts = f.relative_to(base).parts
                if any(part in SKIP_DIRS for part in parts):
                    continue
                # Skip binary files
                if f.suffix in {".pyc", ".so", ".exe", ".bin", ".png", ".jpg", ".gif", ".ico", ".woff", ".woff2"}:
                    continue
                files_to_search.append(f)

    for file_path in files_to_search[:500]:  # Limit files searched
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.split("\n")

            for i, line in enumerate(lines):
                if regex.search(line):
                    rel_path = str(file_path.relative_to(base)) if base.is_dir() else file_path.name
                    # Context
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    context = lines[start:end]

                    results.append(f"{rel_path}:{i + 1}: {line.strip()}")

                    if len(results) >= 50:
                        results.append("...[truncated at 50 matches]")
                        return "\n".join(results)

        except (UnicodeDecodeError, PermissionError):
            continue

    return "\n".join(results) if results else f"No matches for pattern: {pattern}"


def register_search_tools(registry):
    """Register search tools with the tool registry."""
    registry.register("glob_search", "Find files by path pattern", glob_search, permission="free",
                      params={"pattern": "Glob pattern", "path": "Base directory"})
    registry.register("grep_search", "Regex content search", grep_search, permission="free",
                      params={"pattern": "Regex pattern", "path": "Search path", "context_lines": "Context lines"})
