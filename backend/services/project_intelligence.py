"""
MiLyfe Brain - Project Intelligence Service

Provides deep project analysis, mental model building, impact analysis,
and context generation for agents working on the codebase.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from services.file_lock import acquire_lock, release_lock

logger = logging.getLogger(__name__)

# Cached project analysis
_project_cache: Optional[Dict[str, Any]] = None


async def analyze(workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Perform deep analysis of the project structure.

    Examines file types, directory structure, dependencies,
    and build configuration.

    Args:
        workspace_path: Path to analyze (defaults to configured workspace).

    Returns:
        Dict with project analysis results.
    """
    global _project_cache

    from config import settings

    workspace = Path(workspace_path or settings.workspace_dir)

    if not workspace.exists():
        return {"error": "Workspace path does not exist", "path": str(workspace)}

    analysis: Dict[str, Any] = {
        "path": str(workspace),
        "languages": {},
        "file_count": 0,
        "directory_count": 0,
        "total_size_bytes": 0,
        "build_systems": [],
        "frameworks": [],
        "entry_points": [],
    }

    # File extension analysis
    ext_counts: Dict[str, int] = {}
    try:
        for root, dirs, files in os.walk(workspace):
            # Skip hidden/ignored directories
            dirs[:] = [
                d for d in dirs
                if not d.startswith(".")
                and d not in ("node_modules", "__pycache__", "venv", ".venv", "dist", "build")
            ]
            analysis["directory_count"] += 1

            for filename in files:
                filepath = os.path.join(root, filename)
                analysis["file_count"] += 1

                try:
                    analysis["total_size_bytes"] += os.path.getsize(filepath)
                except OSError:
                    pass

                ext = os.path.splitext(filename)[1].lower()
                if ext:
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1

                # Detect build systems
                if filename in ("Makefile", "Dockerfile", "docker-compose.yml"):
                    analysis["build_systems"].append(filename)
                elif filename in ("package.json", "pyproject.toml", "Cargo.toml", "go.mod"):
                    analysis["build_systems"].append(filename)

                # Detect entry points
                if filename in ("main.py", "app.py", "index.ts", "index.js", "main.go"):
                    rel_path = os.path.relpath(filepath, workspace)
                    analysis["entry_points"].append(rel_path)

    except Exception as e:
        logger.error("Project analysis error: %s", e)
        analysis["error"] = str(e)

    # Map extensions to languages
    ext_to_lang = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".go": "Go", ".rs": "Rust", ".java": "Java", ".rb": "Ruby",
        ".cpp": "C++", ".c": "C", ".cs": "C#", ".swift": "Swift",
        ".kt": "Kotlin", ".php": "PHP", ".html": "HTML", ".css": "CSS",
        ".sql": "SQL", ".sh": "Shell", ".yaml": "YAML", ".json": "JSON",
        ".md": "Markdown", ".toml": "TOML",
    }
    for ext, count in ext_counts.items():
        lang = ext_to_lang.get(ext, ext)
        analysis["languages"][lang] = count

    # Detect frameworks
    if ".py" in ext_counts:
        analysis["frameworks"].append("Python")
    if ".ts" in ext_counts or ".tsx" in ext_counts:
        analysis["frameworks"].append("TypeScript")

    _project_cache = analysis
    logger.info(
        "Project analyzed: %d files, %d dirs, %d languages",
        analysis["file_count"], analysis["directory_count"], len(analysis["languages"]),
    )
    return analysis


async def get_mental_model() -> Dict[str, Any]:
    """
    Get or build the project's mental model.

    A high-level abstraction of the project's architecture,
    key components, and their relationships.

    Returns:
        Dict with 'components', 'relationships', 'patterns'.
    """
    global _project_cache

    if _project_cache is None:
        await analyze()

    model: Dict[str, Any] = {
        "components": [],
        "relationships": [],
        "patterns": [],
        "summary": "",
    }

    if _project_cache is None:
        return model

    # Extract components from directory structure
    from config import settings

    workspace = Path(settings.workspace_dir)
    if workspace.exists():
        for item in workspace.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                model["components"].append({
                    "name": item.name,
                    "type": "directory",
                    "files": len(list(item.rglob("*"))) if item.exists() else 0,
                })

    # Detect patterns
    languages = _project_cache.get("languages", {})
    if "Python" in languages:
        model["patterns"].append("Python backend")
    if "TypeScript" in languages or "JavaScript" in languages:
        model["patterns"].append("JavaScript/TypeScript frontend")
    if _project_cache.get("build_systems"):
        model["patterns"].append(f"Build systems: {', '.join(_project_cache['build_systems'][:5])}")

    model["summary"] = (
        f"Project with {_project_cache.get('file_count', 0)} files "
        f"across {len(languages)} languages. "
        f"Primary: {', '.join(list(languages.keys())[:3])}"
    )

    return model


async def get_context_for_agent(
    agent_role: str,
    task: str,
) -> str:
    """
    Generate relevant project context for a specific agent and task.

    Args:
        agent_role: The agent's role.
        task: The task description.

    Returns:
        Formatted context string.
    """
    model = await get_mental_model()

    context_parts: List[str] = [
        f"Project: {model.get('summary', 'Unknown')}",
    ]

    # Add role-specific context
    if agent_role in ("coder", "reviewer"):
        languages = (_project_cache or {}).get("languages", {})
        if languages:
            top_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:5]
            context_parts.append(f"Languages: {', '.join(l for l, _ in top_langs)}")

    if model["patterns"]:
        context_parts.append(f"Patterns: {', '.join(model['patterns'][:3])}")

    return "\n".join(context_parts)


async def acquire_file_lock(path: str, agent_id: str) -> bool:
    """
    Acquire a file lock (delegates to file_lock service).

    Args:
        path: File path to lock.
        agent_id: Requesting agent ID.

    Returns:
        True if lock acquired.
    """
    return acquire_lock(path, agent_id)


async def release_file_lock(path: str, agent_id: str) -> bool:
    """
    Release a file lock (delegates to file_lock service).

    Args:
        path: File path to unlock.
        agent_id: Releasing agent ID.

    Returns:
        True if lock released.
    """
    return release_lock(path, agent_id)


async def get_impact_analysis(file_path: str) -> Dict[str, Any]:
    """
    Analyze the impact of modifying a specific file.

    Examines imports, dependents, and related test files.

    Args:
        file_path: Path to the file being modified.

    Returns:
        Dict with 'dependents', 'dependencies', 'test_files', 'risk_level'.
    """
    from config import settings

    workspace = Path(settings.workspace_dir)
    result: Dict[str, Any] = {
        "file": file_path,
        "dependents": [],
        "dependencies": [],
        "test_files": [],
        "risk_level": "low",
    }

    abs_path = Path(file_path)
    if not abs_path.is_absolute():
        abs_path = workspace / file_path

    if not abs_path.exists():
        result["error"] = "File not found"
        return result

    filename = abs_path.name
    stem = abs_path.stem

    # Find potential test files
    try:
        for test_path in workspace.rglob(f"test_{stem}*"):
            result["test_files"].append(str(test_path.relative_to(workspace)))
        for test_path in workspace.rglob(f"{stem}_test*"):
            result["test_files"].append(str(test_path.relative_to(workspace)))
    except Exception:
        pass

    # Simple import analysis (for Python files)
    if abs_path.suffix == ".py":
        try:
            content = abs_path.read_text(errors="ignore")
            import re

            imports = re.findall(r"^(?:from|import)\s+(\S+)", content, re.MULTILINE)
            result["dependencies"] = imports[:20]
        except Exception:
            pass

    # Determine risk level
    if any(pattern in str(file_path) for pattern in ["config", "main", "database", "__init__"]):
        result["risk_level"] = "high"
    elif result["test_files"]:
        result["risk_level"] = "medium"

    return result
