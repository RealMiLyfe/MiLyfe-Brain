"""File search tools for MiLyfe Brain.

Provides glob-based file search and grep-style content search.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)

# Directories to skip during search
SKIP_DIRS = frozenset({
    ".git",
    "node_modules",
    "__pycache__",
    ".next",
    "venv",
    ".venv",
    "dist",
    ".mypy_cache",
    ".pytest_cache",
})

WORKSPACE_DIR = Path(settings.workspace_dir).resolve()


def _should_skip(path: Path) -> bool:
    """Check if a path should be skipped."""
    return any(part in SKIP_DIRS for part in path.parts)


async def glob_search(
    pattern: str,
    root: Optional[str] = None,
) -> str:
    """Search for files matching a glob pattern.

    Args:
        pattern: Glob pattern (e.g. '**/*.py', '*.json').
        root: Root directory to search from. Defaults to workspace.

    Returns:
        Newline-separated list of matching file paths.
    """
    search_root = Path(root).resolve() if root else WORKSPACE_DIR

    if not search_root.exists():
        return f"[ERROR] Directory not found: {search_root}"

    matches: list[str] = []
    try:
        for match in sorted(search_root.glob(pattern)):
            if _should_skip(match):
                continue
            relative = match.relative_to(search_root)
            matches.append(str(relative))
    except Exception as exc:
        return f"[ERROR] Glob search failed: {exc}"

    if not matches:
        return f"No files matching '{pattern}' in {search_root}"

    header = f"Found {len(matches)} match(es) for '{pattern}':\n"
    logger.info("glob_search: pattern=%r root=%s matches=%d", pattern, search_root, len(matches))
    return header + "\n".join(matches)



async def grep_search(
    pattern: str,
    path: Optional[str] = None,
    context_lines: int = 2,
) -> str:
    """Search file contents for a regex pattern with context.

    Args:
        pattern: Regex pattern to search for.
        path: File or directory to search in. Defaults to workspace.
        context_lines: Number of context lines above/below each match.

    Returns:
        Formatted search results with file paths, line numbers, and context.
    """
    search_path = Path(path).resolve() if path else WORKSPACE_DIR

    if not search_path.exists():
        return f"[ERROR] Path not found: {search_path}"

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return f"[ERROR] Invalid regex pattern: {exc}"

    results: list[str] = []
    files_to_search: list[Path] = []

    if search_path.is_file():
        files_to_search = [search_path]
    else:
        for file_path in sorted(search_path.rglob("*")):
            if not file_path.is_file():
                continue
            if _should_skip(file_path):
                continue
            # Skip binary files by extension
            if file_path.suffix in {".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".png", ".jpg", ".gif", ".ico"}:
                continue
            files_to_search.append(file_path)

    for file_path in files_to_search:
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except (PermissionError, OSError):
            continue

        file_matches: list[str] = []
        for i, line in enumerate(lines):
            if regex.search(line):
                # Gather context
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context_block: list[str] = []
                for j in range(start, end):
                    marker = ">" if j == i else " "
                    context_block.append(f"  {marker} {j + 1:4d} | {lines[j]}")
                file_matches.append("\n".join(context_block))

        if file_matches:
            relative = file_path.relative_to(search_path) if search_path.is_dir() else file_path.name
            results.append(f"── {relative} ──\n" + "\n\n".join(file_matches))

    if not results:
        return f"No matches for pattern '{pattern}' in {search_path}"

    total_matches = sum(r.count("\n>") + r.count("\n >") for r in results)
    header = f"grep: {len(results)} file(s) matched for '{pattern}':\n\n"
    logger.info("grep_search: pattern=%r path=%s files=%d", pattern, search_path, len(results))
    return header + "\n\n".join(results)
