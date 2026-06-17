"""MiLyfe Brain — Project Intelligence Service.

Auto-detect project type, dependency graph, hot files, conflict detection,
file importance ranking, and project mental model for agents.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

from config import settings

logger = structlog.get_logger()


# ─── Project Type Definitions ───────────────────────────────────

PROJECT_SIGNATURES = {
    "python_fastapi": {
        "indicators": ["requirements.txt", "main.py", "pyproject.toml"],
        "content_hints": {"main.py": ["fastapi", "FastAPI", "uvicorn"]},
        "framework": "FastAPI",
        "language": "python",
    },
    "python_django": {
        "indicators": ["manage.py", "settings.py", "urls.py"],
        "content_hints": {"manage.py": ["django"]},
        "framework": "Django",
        "language": "python",
    },
    "python_flask": {
        "indicators": ["app.py", "requirements.txt"],
        "content_hints": {"app.py": ["flask", "Flask"]},
        "framework": "Flask",
        "language": "python",
    },
    "python_generic": {
        "indicators": ["setup.py", "pyproject.toml", "requirements.txt"],
        "content_hints": {},
        "framework": None,
        "language": "python",
    },
    "node_nextjs": {
        "indicators": ["package.json", "next.config.ts", "next.config.js"],
        "content_hints": {"package.json": ["next", "react"]},
        "framework": "Next.js",
        "language": "typescript",
    },
    "node_react": {
        "indicators": ["package.json", "src/App.tsx", "src/App.jsx"],
        "content_hints": {"package.json": ["react", "react-dom"]},
        "framework": "React",
        "language": "typescript",
    },
    "node_express": {
        "indicators": ["package.json", "server.js", "index.js"],
        "content_hints": {"package.json": ["express"]},
        "framework": "Express",
        "language": "javascript",
    },
    "rust": {
        "indicators": ["Cargo.toml", "src/main.rs", "src/lib.rs"],
        "content_hints": {},
        "framework": None,
        "language": "rust",
    },
    "go": {
        "indicators": ["go.mod", "main.go"],
        "content_hints": {},
        "framework": None,
        "language": "go",
    },
    "docker_compose": {
        "indicators": ["docker-compose.yml", "docker-compose.yaml", "Dockerfile"],
        "content_hints": {},
        "framework": "Docker",
        "language": "multi",
    },
}


class ProjectIntelligence:
    """Builds and maintains a mental model of the project for agents."""

    def __init__(self):
        self._project_type: Optional[str] = None
        self._language: Optional[str] = None
        self._framework: Optional[str] = None
        self._dependencies: Dict[str, List[str]] = {}  # file -> [imports]
        self._import_graph: Dict[str, Set[str]] = defaultdict(set)  # file -> files it imports
        self._imported_by: Dict[str, Set[str]] = defaultdict(set)  # file -> files that import it
        self._hot_files: Counter = Counter()  # file -> modification count
        self._file_importance: Dict[str, float] = {}  # file -> importance score
        self._conflicts: List[Dict] = []
        self._active_editors: Dict[str, str] = {}  # file -> agent_id currently editing
        self._last_analysis: Optional[datetime] = None
        self._project_summary: str = ""

    async def analyze(self) -> Dict:
        """Run full project analysis."""
        workspace = Path(settings.workspace_dir)
        if not workspace.exists():
            return {"error": "Workspace not found"}

        # Detect project type
        self._detect_project_type(workspace)

        # Build dependency graph
        await self._build_dependency_graph(workspace)

        # Calculate file importance
        self._calculate_importance()

        # Generate summary
        self._generate_summary(workspace)

        self._last_analysis = datetime.utcnow()

        return self.get_mental_model()

    def get_mental_model(self) -> Dict:
        """Get the full project mental model (for agent context injection)."""
        return {
            "project_type": self._project_type,
            "language": self._language,
            "framework": self._framework,
            "summary": self._project_summary,
            "key_files": self._get_key_files(limit=10),
            "hot_files": self._hot_files.most_common(10),
            "dependency_depth": self._max_dependency_depth(),
            "total_tracked_files": len(self._file_importance),
            "last_analysis": self._last_analysis.isoformat() if self._last_analysis else None,
        }

    def get_context_for_agent(self, task: str = "") -> str:
        """Get a compact project context string for agent prompts."""
        if not self._project_type:
            return ""

        parts = [f"[Project: {self._framework or self._language or 'Unknown'} ({self._project_type})]"]

        if self._project_summary:
            parts.append(self._project_summary)

        # Add relevant files based on task keywords
        if task:
            relevant = self._find_relevant_files(task, limit=5)
            if relevant:
                parts.append("Relevant files: " + ", ".join(relevant))

        return "\n".join(parts)

    def record_file_access(self, path: str, agent_id: str = ""):
        """Record that a file was accessed/modified (for hot file tracking)."""
        self._hot_files[path] += 1

    def acquire_file_lock(self, path: str, agent_id: str) -> bool:
        """Try to acquire edit lock on a file (conflict prevention)."""
        if path in self._active_editors and self._active_editors[path] != agent_id:
            self._conflicts.append({
                "file": path,
                "holder": self._active_editors[path],
                "requester": agent_id,
                "timestamp": datetime.utcnow().isoformat(),
            })
            return False
        self._active_editors[path] = agent_id
        return True

    def release_file_lock(self, path: str, agent_id: str):
        """Release edit lock on a file."""
        if self._active_editors.get(path) == agent_id:
            del self._active_editors[path]

    def get_conflicts(self) -> List[Dict]:
        """Get recent file conflicts."""
        return self._conflicts[-20:]

    def get_dependents(self, file_path: str) -> List[str]:
        """Get files that depend on (import from) the given file."""
        return list(self._imported_by.get(file_path, set()))

    def get_dependencies(self, file_path: str) -> List[str]:
        """Get files that the given file imports/depends on."""
        return list(self._import_graph.get(file_path, set()))

    def get_impact_analysis(self, file_path: str) -> Dict:
        """Analyze the impact of changing a file."""
        direct_dependents = self.get_dependents(file_path)
        all_affected: Set[str] = set()

        # BFS to find all transitively affected files
        queue = list(direct_dependents)
        while queue:
            current = queue.pop(0)
            if current not in all_affected:
                all_affected.add(current)
                queue.extend(self._imported_by.get(current, set()) - all_affected)

        return {
            "file": file_path,
            "direct_dependents": direct_dependents,
            "total_affected": len(all_affected),
            "affected_files": sorted(all_affected)[:20],
            "risk_level": "high" if len(all_affected) > 10 else "medium" if len(all_affected) > 3 else "low",
            "importance": self._file_importance.get(file_path, 0),
        }

    # ─── Project Type Detection ─────────────────────────────────

    def _detect_project_type(self, workspace: Path):
        """Detect project type from file signatures and content."""
        scores: Dict[str, int] = defaultdict(int)

        files_present = {f.name for f in workspace.iterdir() if f.is_file()}
        # Also check one level deep
        for d in workspace.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                files_present.update(f"{d.name}/{f.name}" for f in d.iterdir() if f.is_file())

        for proj_type, sig in PROJECT_SIGNATURES.items():
            # Check indicator files
            for indicator in sig["indicators"]:
                if indicator in files_present or (workspace / indicator).exists():
                    scores[proj_type] += 2

            # Check content hints
            for filename, hints in sig.get("content_hints", {}).items():
                filepath = workspace / filename
                if filepath.exists():
                    try:
                        content = filepath.read_text(errors="replace")[:5000]
                        for hint in hints:
                            if hint in content:
                                scores[proj_type] += 3
                    except Exception:
                        pass

        if scores:
            best = max(scores, key=scores.get)
            sig = PROJECT_SIGNATURES[best]
            self._project_type = best
            self._language = sig["language"]
            self._framework = sig["framework"]
            logger.info("project_detected", type=best, language=sig["language"], framework=sig["framework"])
        else:
            self._project_type = "unknown"
            self._language = "unknown"

    # ─── Dependency Graph ───────────────────────────────────────

    async def _build_dependency_graph(self, workspace: Path):
        """Build import/dependency graph for the project."""
        self._import_graph.clear()
        self._imported_by.clear()

        if self._language == "python":
            await self._build_python_graph(workspace)
        elif self._language in ("typescript", "javascript"):
            await self._build_js_graph(workspace)

    async def _build_python_graph(self, workspace: Path):
        """Build Python import graph."""
        py_files = [f for f in workspace.rglob("*.py")
                    if not any(p.startswith(".") or p in ("node_modules", "__pycache__", "venv")
                              for p in f.relative_to(workspace).parts)]

        import_pattern = re.compile(r"^(?:from|import)\s+([\w.]+)", re.MULTILINE)

        for f in py_files:
            rel = str(f.relative_to(workspace))
            try:
                content = f.read_text(errors="replace")
                imports = import_pattern.findall(content)

                for imp in imports:
                    # Resolve relative imports to file paths
                    imp_path = imp.replace(".", "/") + ".py"
                    if (workspace / imp_path).exists():
                        self._import_graph[rel].add(imp_path)
                        self._imported_by[imp_path].add(rel)
                    # Try as package
                    imp_pkg = imp.replace(".", "/") + "/__init__.py"
                    if (workspace / imp_pkg).exists():
                        self._import_graph[rel].add(imp_pkg)
                        self._imported_by[imp_pkg].add(rel)
            except Exception:
                pass

    async def _build_js_graph(self, workspace: Path):
        """Build JavaScript/TypeScript import graph."""
        extensions = (".ts", ".tsx", ".js", ".jsx")
        js_files = [f for f in workspace.rglob("*")
                    if f.suffix in extensions
                    and not any(p in ("node_modules", ".next", "dist")
                               for p in f.relative_to(workspace).parts)]

        import_pattern = re.compile(r"""(?:import|from)\s+['"]([./][^'"]+)['"]""")

        for f in js_files:
            rel = str(f.relative_to(workspace))
            try:
                content = f.read_text(errors="replace")
                imports = import_pattern.findall(content)

                for imp in imports:
                    # Resolve relative path
                    resolved = (f.parent / imp).resolve()
                    for ext in ("", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx"):
                        candidate = Path(str(resolved) + ext)
                        if candidate.exists():
                            target_rel = str(candidate.relative_to(workspace))
                            self._import_graph[rel].add(target_rel)
                            self._imported_by[target_rel].add(rel)
                            break
            except Exception:
                pass

    # ─── File Importance ────────────────────────────────────────

    def _calculate_importance(self):
        """Calculate importance score for each file (PageRank-inspired)."""
        all_files = set(self._import_graph.keys()) | set(self._imported_by.keys())

        for f in all_files:
            # Score based on: how many files import this + how hot it is
            import_count = len(self._imported_by.get(f, set()))
            hot_count = self._hot_files.get(f, 0)
            depth = self._dependency_depth(f)

            score = (import_count * 3) + (hot_count * 1) + (depth * 0.5)
            self._file_importance[f] = score

    def _dependency_depth(self, file_path: str, visited: Set[str] = None) -> int:
        """Calculate how deep in the dependency tree a file sits."""
        if visited is None:
            visited = set()
        if file_path in visited:
            return 0
        visited.add(file_path)

        deps = self._import_graph.get(file_path, set())
        if not deps:
            return 0
        return 1 + max(self._dependency_depth(d, visited) for d in deps)

    def _max_dependency_depth(self) -> int:
        """Get the maximum dependency depth in the project."""
        if not self._import_graph:
            return 0
        return max((self._dependency_depth(f) for f in self._import_graph), default=0)

    # ─── Helpers ────────────────────────────────────────────────

    def _get_key_files(self, limit: int = 10) -> List[Dict]:
        """Get the most important files."""
        sorted_files = sorted(self._file_importance.items(), key=lambda x: -x[1])
        return [
            {"path": path, "importance": score, "dependents": len(self._imported_by.get(path, set()))}
            for path, score in sorted_files[:limit]
        ]

    def _find_relevant_files(self, task: str, limit: int = 5) -> List[str]:
        """Find files relevant to a task description."""
        task_lower = task.lower()
        task_words = set(task_lower.split())

        scored: List[Tuple[float, str]] = []
        for file_path in self._file_importance:
            # Score by word overlap with path
            path_words = set(re.split(r"[/._\-]", file_path.lower()))
            overlap = len(task_words & path_words)
            if overlap > 0:
                score = overlap + self._file_importance.get(file_path, 0) * 0.1
                scored.append((score, file_path))

        scored.sort(key=lambda x: -x[0])
        return [path for _, path in scored[:limit]]

    def _generate_summary(self, workspace: Path):
        """Generate a one-paragraph project summary."""
        parts = []

        if self._framework:
            parts.append(f"This is a {self._framework} project")
        elif self._language:
            parts.append(f"This is a {self._language} project")

        file_count = len(self._file_importance)
        if file_count:
            parts.append(f"with {file_count} tracked source files")

        if self._import_graph:
            parts.append(f"and {sum(len(v) for v in self._import_graph.values())} import relationships")

        key_files = self._get_key_files(3)
        if key_files:
            names = [Path(f["path"]).name for f in key_files]
            parts.append(f"(key files: {', '.join(names)})")

        self._project_summary = ". ".join(parts) + "." if parts else ""


# Singleton
project_intelligence = ProjectIntelligence()
