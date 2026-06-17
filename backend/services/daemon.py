"""
MiLyfe Brain - Daemon Service

Background daemon providing:
  - File change detection (content-hash based, every 3s)
  - Pattern analysis and proactive suggestions (every 30s)
  - Codebase health scoring and health checks (every 5min)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DaemonService:
    """Background file watcher and proactive intelligence service."""

    def __init__(self) -> None:
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None

        # File watching state
        self._file_hashes: Dict[str, str] = {}
        self._changed_files: List[str] = []

        # Timing counters (in seconds)
        self._file_check_interval: float = 3.0
        self._pattern_analysis_interval: float = 30.0
        self._health_check_interval: float = 300.0

        # Timestamps of last runs
        self._last_file_check: float = 0.0
        self._last_pattern_analysis: float = 0.0
        self._last_health_check: float = 0.0

        # Health score (0.0 - 1.0)
        self._health_score: float = 1.0
        self._suggestions: List[Dict[str, str]] = []

    async def start(self) -> None:
        """Start the daemon main loop."""
        if self._running:
            logger.warning("DaemonService already running")
            return

        self._running = True
        self._started_at = datetime.utcnow()
        self._task = asyncio.create_task(self._main_loop())
        logger.info("DaemonService started")

    async def stop(self) -> None:
        """Stop the daemon."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._started_at = None
        logger.info("DaemonService stopped")

    def get_status(self) -> Dict:
        """Return current daemon status."""
        uptime = 0.0
        if self._started_at:
            uptime = (datetime.utcnow() - self._started_at).total_seconds()

        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "health_score": self._health_score,
            "watched_files": len(self._file_hashes),
            "recent_changes": len(self._changed_files),
            "suggestions": self._suggestions[-5:],  # last 5 suggestions
        }

    async def _main_loop(self) -> None:
        """
        Main daemon loop with staggered checks:
          - File changes: every 3 seconds
          - Pattern analysis: every 30 seconds
          - Health check: every 5 minutes
        """
        while self._running:
            try:
                now = time.time()

                # File change detection (every 3s)
                if (now - self._last_file_check) >= self._file_check_interval:
                    await self._check_file_changes()
                    self._last_file_check = now

                # Pattern analysis (every 30s)
                if (now - self._last_pattern_analysis) >= self._pattern_analysis_interval:
                    await self._analyze_patterns()
                    self._last_pattern_analysis = now

                # Health check (every 5min)
                if (now - self._last_health_check) >= self._health_check_interval:
                    await self._run_health_check()
                    self._last_health_check = now

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Daemon loop error: %s", e)

            await asyncio.sleep(1.0)  # Tick every second

    async def _check_file_changes(self) -> None:
        """Detect file changes using content hashing."""
        from config import settings

        workspace = Path(settings.workspace_dir)
        if not workspace.exists():
            return

        new_changes: List[str] = []
        current_hashes: Dict[str, str] = {}

        try:
            for root, _dirs, files in os.walk(workspace):
                # Skip hidden directories and common ignore patterns
                root_path = Path(root)
                if any(part.startswith(".") for part in root_path.parts):
                    continue
                if "node_modules" in root_path.parts or "__pycache__" in root_path.parts:
                    continue

                for filename in files:
                    filepath = os.path.join(root, filename)
                    try:
                        stat = os.stat(filepath)
                        # Skip large files (> 1MB)
                        if stat.st_size > 1_048_576:
                            continue

                        content_hash = await self._hash_file(filepath)
                        current_hashes[filepath] = content_hash

                        # Detect changes
                        old_hash = self._file_hashes.get(filepath)
                        if old_hash is not None and old_hash != content_hash:
                            new_changes.append(filepath)
                    except (OSError, PermissionError):
                        continue

            # Detect deleted files
            deleted = set(self._file_hashes.keys()) - set(current_hashes.keys())
            for deleted_path in deleted:
                new_changes.append(f"[DELETED] {deleted_path}")

            # Update state
            self._file_hashes = current_hashes

            if new_changes:
                self._changed_files = new_changes[-50:]  # Keep last 50 changes
                logger.debug("Detected %d file changes", len(new_changes))

        except Exception as e:
            logger.debug("File change detection error: %s", e)

    async def _hash_file(self, filepath: str) -> str:
        """Compute SHA-256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(
                None, self._read_file_bytes, filepath
            )
            hasher.update(content)
        except Exception:
            # Use mtime as fallback hash
            try:
                mtime = os.path.getmtime(filepath)
                hasher.update(str(mtime).encode())
            except OSError:
                hasher.update(filepath.encode())
        return hasher.hexdigest()

    @staticmethod
    def _read_file_bytes(filepath: str) -> bytes:
        """Read file bytes synchronously (for executor)."""
        with open(filepath, "rb") as f:
            return f.read()

    async def _analyze_patterns(self) -> None:
        """Analyze recent changes for patterns and generate proactive suggestions."""
        if not self._changed_files:
            return

        suggestions: List[Dict[str, str]] = []

        # Pattern: Many files changed in same directory → possible refactoring
        dir_counts: Dict[str, int] = {}
        for filepath in self._changed_files:
            if filepath.startswith("[DELETED]"):
                continue
            dirname = os.path.dirname(filepath)
            dir_counts[dirname] = dir_counts.get(dirname, 0) + 1

        for dirname, count in dir_counts.items():
            if count >= 5:
                suggestions.append({
                    "type": "refactoring",
                    "message": f"High activity in {dirname} ({count} files changed). Consider running tests.",
                    "priority": "medium",
                })

        # Pattern: Test files changed → suggest running tests
        test_changes = [f for f in self._changed_files if "test" in f.lower()]
        if test_changes:
            suggestions.append({
                "type": "testing",
                "message": f"{len(test_changes)} test file(s) modified. Consider running the test suite.",
                "priority": "low",
            })

        # Pattern: Config files changed → warn about potential impact
        config_changes = [
            f for f in self._changed_files
            if any(ext in f for ext in [".env", ".yml", ".yaml", ".toml", ".json", ".cfg"])
        ]
        if config_changes:
            suggestions.append({
                "type": "configuration",
                "message": "Configuration files changed. Verify environment settings are correct.",
                "priority": "high",
            })

        if suggestions:
            self._suggestions.extend(suggestions)
            # Keep only last 20 suggestions
            self._suggestions = self._suggestions[-20:]

        # Clear processed changes
        self._changed_files = []

    async def _run_health_check(self) -> None:
        """Compute codebase health score and check service connectivity."""
        score = 1.0
        issues: List[str] = []

        # Check Ollama connectivity
        try:
            import httpx

            from config import settings

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                if resp.status_code != 200:
                    score -= 0.2
                    issues.append("Ollama not responding properly")
        except Exception:
            score -= 0.2
            issues.append("Ollama unreachable")

        # Check ChromaDB connectivity
        try:
            import httpx

            from config import settings

            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{settings.chroma_url}/api/v1/heartbeat")
                if resp.status_code != 200:
                    score -= 0.15
                    issues.append("ChromaDB not responding")
        except Exception:
            score -= 0.15
            issues.append("ChromaDB unreachable")

        # Check workspace exists
        from config import settings

        workspace = Path(settings.workspace_dir)
        if not workspace.exists():
            score -= 0.1
            issues.append("Workspace directory missing")

        # Check database
        from memory.database import async_session_factory

        if async_session_factory is None:
            score -= 0.3
            issues.append("Database not initialized")

        self._health_score = max(0.0, score)

        if issues:
            logger.debug("Health check issues: %s (score=%.2f)", issues, self._health_score)
        else:
            logger.debug("Health check passed (score=%.2f)", self._health_score)


daemon = DaemonService()
