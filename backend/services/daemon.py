"""MiLyfe Brain — Ambient Intelligence Daemon.

Beyond file watching: proactive suggestions, pattern recognition,
codebase health monitoring, morning briefings, auto-triggered playbooks.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import structlog

from config import settings
from models.schemas import DaemonStatus

logger = structlog.get_logger()


class FileChange:
    """Represents a detected file change."""

    def __init__(self, path: str, change_type: str, timestamp: datetime):
        self.path = path
        self.change_type = change_type  # "created", "modified", "deleted"
        self.timestamp = timestamp


class DaemonService:
    """Ambient intelligence daemon — watches, learns, suggests, acts.

    Capabilities:
    1. File watching (new/modified/deleted detection with content hashing)
    2. Pattern recognition (detects repeated manual operations)
    3. Proactive suggestions (untested code, missing docs, security issues)
    4. Codebase health scoring (test coverage proxy, stale files, TODOs)
    5. Morning briefing generation
    6. Auto-triggered playbook rules
    7. Activity tracking for analytics
    """

    def __init__(self):
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._events_processed: int = 0
        self._last_event: Optional[datetime] = None
        self._watching: List[str] = []

        # File tracking
        self._file_hashes: Dict[str, str] = {}  # path -> content hash
        self._file_mtimes: Dict[str, float] = {}  # path -> mtime

        # Pattern tracking
        self._change_history: List[FileChange] = []
        self._command_history: List[Dict] = []
        self._user_patterns: Counter = Counter()

        # Health tracking
        self._health_score: float = 0.0
        self._health_issues: List[Dict] = []
        self._last_health_check: Optional[datetime] = None

        # Suggestions
        self._pending_suggestions: List[Dict] = []
        self._dismissed_suggestions: Set[str] = set()

        # Auto-trigger rules
        self._trigger_rules: List[Dict] = []
        self._last_briefing: Optional[datetime] = None

    async def start(self):
        """Start the ambient daemon."""
        self._running = True
        workspace = Path(settings.workspace_dir)
        workspace.mkdir(parents=True, exist_ok=True)
        self._watching = [str(workspace)]

        # Initial scan
        await self._full_scan()

        # Load trigger rules
        self._load_trigger_rules()

        # Start background loops
        self._task = asyncio.create_task(self._main_loop())
        logger.info("ambient_daemon_started", watching=self._watching)

    async def stop(self):
        """Stop the daemon."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("ambient_daemon_stopped")

    def get_status(self) -> DaemonStatus:
        return DaemonStatus(
            running=self._running,
            watching_paths=self._watching,
            events_processed=self._events_processed,
            last_event=self._last_event,
        )

    def get_extended_status(self) -> Dict:
        """Get full daemon status with intelligence data."""
        return {
            "running": self._running,
            "watching_paths": self._watching,
            "events_processed": self._events_processed,
            "last_event": self._last_event.isoformat() if self._last_event else None,
            "tracked_files": len(self._file_hashes),
            "health_score": self._health_score,
            "health_issues": self._health_issues[:10],
            "pending_suggestions": self._pending_suggestions[:5],
            "detected_patterns": self._user_patterns.most_common(5),
            "trigger_rules": len(self._trigger_rules),
            "last_briefing": self._last_briefing.isoformat() if self._last_briefing else None,
        }

    def get_suggestions(self) -> List[Dict]:
        """Get current proactive suggestions."""
        return [s for s in self._pending_suggestions if s["id"] not in self._dismissed_suggestions]

    def dismiss_suggestion(self, suggestion_id: str):
        """Dismiss a suggestion."""
        self._dismissed_suggestions.add(suggestion_id)

    async def generate_briefing(self) -> Dict:
        """Generate a morning briefing / status report."""
        from services.daily_digest import generate_daily_digest

        digest = await generate_daily_digest()
        health = await self._check_codebase_health()

        briefing = {
            "generated_at": datetime.utcnow().isoformat(),
            "digest": digest,
            "health": health,
            "suggestions": self.get_suggestions()[:5],
            "recent_changes": [
                {"path": c.path, "type": c.change_type, "time": c.timestamp.isoformat()}
                for c in self._change_history[-10:]
            ],
            "patterns_detected": [
                {"pattern": p, "count": c}
                for p, c in self._user_patterns.most_common(3)
            ],
        }

        self._last_briefing = datetime.utcnow()
        return briefing

    def record_command(self, command: str, context: Dict = None):
        """Record a user command for pattern detection."""
        self._command_history.append({
            "command": command,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
        })
        # Track patterns
        cmd_key = command.split()[0] if command.split() else ""
        self._user_patterns[cmd_key] += 1

        # Keep history bounded
        if len(self._command_history) > 500:
            self._command_history = self._command_history[-500:]

    # ─── Main Loop ──────────────────────────────────────────────

    async def _main_loop(self):
        """Main daemon loop — orchestrates all intelligence tasks."""
        cycle = 0
        while self._running:
            try:
                cycle += 1

                # Every 3 seconds: check file changes
                await self._check_changes()

                # Every 30 seconds: pattern analysis
                if cycle % 10 == 0:
                    await self._analyze_patterns()

                # Every 5 minutes: health check
                if cycle % 100 == 0:
                    await self._check_codebase_health()

                # Every hour: generate suggestions
                if cycle % 1200 == 0:
                    await self._generate_suggestions()

                # Every 24h: morning briefing
                if self._should_generate_briefing():
                    await self.generate_briefing()

                await asyncio.sleep(3)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("daemon_loop_error", error=str(e))
                await asyncio.sleep(10)

    # ─── File Watching (Content-Hash Based) ─────────────────────

    async def _full_scan(self):
        """Full workspace scan with content hashing."""
        workspace = Path(settings.workspace_dir)
        if not workspace.exists():
            return

        for f in workspace.rglob("*"):
            if f.is_file() and self._should_track(f, workspace):
                path_str = str(f)
                try:
                    stat = f.stat()
                    self._file_mtimes[path_str] = stat.st_mtime
                    # Hash small files for change detection
                    if stat.st_size < 1_000_000:  # < 1MB
                        content = f.read_bytes()
                        self._file_hashes[path_str] = hashlib.md5(content).hexdigest()
                except (PermissionError, OSError):
                    pass

    async def _check_changes(self):
        """Detect file changes using mtime + hash comparison."""
        workspace = Path(settings.workspace_dir)
        if not workspace.exists():
            return

        current_files: Dict[str, float] = {}
        changes: List[FileChange] = []

        for f in workspace.rglob("*"):
            if f.is_file() and self._should_track(f, workspace):
                path_str = str(f)
                try:
                    stat = f.stat()
                    current_files[path_str] = stat.st_mtime

                    if path_str not in self._file_mtimes:
                        # New file
                        changes.append(FileChange(path_str, "created", datetime.utcnow()))
                    elif stat.st_mtime > self._file_mtimes.get(path_str, 0):
                        # Modified (verify with hash for small files)
                        if stat.st_size < 1_000_000:
                            new_hash = hashlib.md5(f.read_bytes()).hexdigest()
                            if new_hash != self._file_hashes.get(path_str):
                                changes.append(FileChange(path_str, "modified", datetime.utcnow()))
                                self._file_hashes[path_str] = new_hash
                        else:
                            changes.append(FileChange(path_str, "modified", datetime.utcnow()))
                except (PermissionError, OSError):
                    pass

        # Detect deletions
        deleted = set(self._file_mtimes.keys()) - set(current_files.keys())
        for path_str in deleted:
            changes.append(FileChange(path_str, "deleted", datetime.utcnow()))
            self._file_hashes.pop(path_str, None)

        self._file_mtimes = current_files

        if changes:
            self._events_processed += len(changes)
            self._last_event = datetime.utcnow()
            self._change_history.extend(changes)

            # Bound history
            if len(self._change_history) > 1000:
                self._change_history = self._change_history[-1000:]

            # Check trigger rules
            await self._check_triggers(changes)

            # Emit events
            for change in changes[:5]:  # Limit event emission
                try:
                    from api.routes.streaming import emit_event
                    from models.schemas import EventType
                    emit_event(
                        event_type=EventType.ACTION,
                        data={
                            "daemon": True,
                            "change_type": change.change_type,
                            "path": change.path,
                        },
                    )
                except Exception:
                    pass

    def _should_track(self, path: Path, workspace: Path) -> bool:
        """Determine if a file should be tracked."""
        rel = path.relative_to(workspace)
        skip_dirs = {".git", "node_modules", "__pycache__", ".next", "venv", ".venv", ".isolated", ".runs", ".screenshots"}
        skip_exts = {".pyc", ".pyo", ".so", ".o", ".class"}

        if any(part in skip_dirs for part in rel.parts):
            return False
        if path.suffix in skip_exts:
            return False
        if any(part.startswith(".") for part in rel.parts if part != ".milyfe"):
            return False
        return True

    # ─── Pattern Analysis ───────────────────────────────────────

    async def _analyze_patterns(self):
        """Detect repeated user patterns and suggest automation."""
        # Detect repeated file edit patterns
        recent_changes = self._change_history[-50:]
        if len(recent_changes) < 5:
            return

        # Group changes by file extension
        ext_counter: Counter = Counter()
        for change in recent_changes:
            ext = Path(change.path).suffix
            ext_counter[ext] += 1

        # Detect burst activity (many changes to same file type)
        for ext, count in ext_counter.most_common(3):
            if count >= 5:
                pattern_key = f"burst_{ext}"
                if pattern_key not in self._dismissed_suggestions:
                    self._add_suggestion(
                        id=pattern_key,
                        type="pattern",
                        title=f"Frequent {ext} file changes detected",
                        message=f"You've modified {count} {ext} files recently. Want to create a playbook to automate this?",
                        action="create_playbook",
                    )

        # Detect repeated command patterns
        if len(self._command_history) >= 10:
            recent_cmds = [c["command"] for c in self._command_history[-10:]]
            repeated = [cmd for cmd, cnt in Counter(recent_cmds).items() if cnt >= 3]
            for cmd in repeated:
                pattern_key = f"repeat_cmd_{hashlib.md5(cmd.encode()).hexdigest()[:8]}"
                if pattern_key not in self._dismissed_suggestions:
                    self._add_suggestion(
                        id=pattern_key,
                        type="automation",
                        title=f"Repeated command: {cmd[:40]}",
                        message=f"You've run this command {Counter(recent_cmds)[cmd]} times. Want to automate it?",
                        action="create_playbook",
                    )

    # ─── Codebase Health ────────────────────────────────────────

    async def _check_codebase_health(self) -> Dict:
        """Analyze codebase health and score it."""
        workspace = Path(settings.workspace_dir)
        if not workspace.exists():
            return {"score": 0, "issues": []}

        issues = []
        score = 100.0

        # Check for TODO/FIXME/HACK comments
        todo_count = 0
        for f in workspace.rglob("*"):
            if f.is_file() and f.suffix in (".py", ".ts", ".tsx", ".js", ".jsx") and self._should_track(f, workspace):
                try:
                    content = f.read_text(errors="replace")
                    todos = content.count("TODO") + content.count("FIXME") + content.count("HACK")
                    todo_count += todos
                except Exception:
                    pass

        if todo_count > 20:
            issues.append({"severity": "warning", "message": f"{todo_count} TODO/FIXME/HACK comments found"})
            score -= min(20, todo_count * 0.5)

        # Check for test files
        test_files = list(workspace.rglob("test_*.py")) + list(workspace.rglob("*.test.ts"))
        source_files = [f for f in workspace.rglob("*.py") if "test" not in f.name and self._should_track(f, workspace)]
        source_files += [f for f in workspace.rglob("*.ts") if "test" not in f.name and self._should_track(f, workspace)]

        if source_files and not test_files:
            issues.append({"severity": "warning", "message": "No test files found"})
            score -= 15

        # Check for large files
        large_files = []
        for f in workspace.rglob("*"):
            if f.is_file() and self._should_track(f, workspace):
                try:
                    if f.stat().st_size > 500_000:  # > 500KB
                        large_files.append(str(f.relative_to(workspace)))
                except Exception:
                    pass

        if large_files:
            issues.append({"severity": "info", "message": f"{len(large_files)} large files (>500KB)"})
            score -= len(large_files) * 2

        # Check for missing README
        if not (workspace / "README.md").exists() and not (workspace / "README").exists():
            issues.append({"severity": "info", "message": "No README file found"})
            score -= 5

        # Check for .env files committed (security)
        for f in workspace.rglob(".env"):
            if self._should_track(f, workspace):
                issues.append({"severity": "critical", "message": f".env file found: {f.relative_to(workspace)}"})
                score -= 20

        # Check stale files (not modified in 90+ days)
        stale_cutoff = time.time() - (90 * 86400)
        stale_count = sum(
            1 for mtime in self._file_mtimes.values()
            if mtime < stale_cutoff
        )
        if stale_count > 10:
            issues.append({"severity": "info", "message": f"{stale_count} files not modified in 90+ days"})

        self._health_score = max(0, min(100, score))
        self._health_issues = issues
        self._last_health_check = datetime.utcnow()

        return {"score": self._health_score, "issues": issues}

    # ─── Proactive Suggestions ──────────────────────────────────

    async def _generate_suggestions(self):
        """Generate proactive suggestions based on workspace state."""
        workspace = Path(settings.workspace_dir)
        if not workspace.exists():
            return

        # Suggest tests for untested code
        py_files = [f for f in workspace.rglob("*.py") if self._should_track(f, workspace) and "test" not in f.name]
        test_files = {f.name.replace("test_", "") for f in workspace.rglob("test_*.py")}

        untested = [f for f in py_files if f.stem not in test_files and f.name != "__init__.py"]
        if untested and len(untested) > 3:
            self._add_suggestion(
                id="suggest_tests",
                type="quality",
                title="Untested modules detected",
                message=f"{len(untested)} Python modules have no corresponding test files. Generate tests?",
                action="generate_tests",
                data={"files": [str(f.relative_to(workspace)) for f in untested[:5]]},
            )

        # Suggest documentation for undocumented code
        for f in py_files[:20]:
            try:
                content = f.read_text(errors="replace")
                if len(content) > 500 and '"""' not in content and "'''" not in content:
                    self._add_suggestion(
                        id=f"doc_{f.stem}",
                        type="documentation",
                        title=f"Missing docstrings: {f.name}",
                        message=f"{f.name} has no docstrings. Generate documentation?",
                        action="generate_docs",
                        data={"file": str(f.relative_to(workspace))},
                    )
                    break  # One at a time
            except Exception:
                pass

    def _add_suggestion(self, id: str, type: str, title: str, message: str, action: str = "", data: Dict = None):
        """Add a suggestion if not already present or dismissed."""
        if id in self._dismissed_suggestions:
            return
        if any(s["id"] == id for s in self._pending_suggestions):
            return

        self._pending_suggestions.append({
            "id": id,
            "type": type,
            "title": title,
            "message": message,
            "action": action,
            "data": data or {},
            "created_at": datetime.utcnow().isoformat(),
        })

        # Bound suggestions
        if len(self._pending_suggestions) > 20:
            self._pending_suggestions = self._pending_suggestions[-20:]

        # Notify
        try:
            from api.routes.streaming import emit_event
            from models.schemas import EventType
            emit_event(
                event_type=EventType.PROGRESS,
                data={"suggestion": {"id": id, "title": title, "type": type}},
            )
        except Exception:
            pass

    # ─── Auto-Trigger Rules ─────────────────────────────────────

    def _load_trigger_rules(self):
        """Load auto-trigger rules from config."""
        # Built-in rules
        self._trigger_rules = [
            {
                "name": "lint_on_python_change",
                "pattern": "*.py",
                "change_type": "modified",
                "action": "suggest",
                "message": "Python file modified. Run linting?",
                "cooldown_seconds": 60,
                "last_triggered": None,
            },
            {
                "name": "test_on_src_change",
                "pattern": "src/**",
                "change_type": "modified",
                "action": "suggest",
                "message": "Source file modified. Run tests?",
                "cooldown_seconds": 120,
                "last_triggered": None,
            },
        ]

        # Load custom rules from workspace config
        workspace = Path(settings.workspace_dir)
        rules_file = workspace / ".milyfe" / "triggers.yaml"
        if rules_file.exists():
            try:
                import yaml
                custom_rules = yaml.safe_load(rules_file.read_text()) or []
                if isinstance(custom_rules, list):
                    self._trigger_rules.extend(custom_rules)
            except Exception:
                pass

    async def _check_triggers(self, changes: List[FileChange]):
        """Check if any trigger rules match the changes."""
        import fnmatch

        now = datetime.utcnow()
        workspace = Path(settings.workspace_dir)

        for rule in self._trigger_rules:
            # Check cooldown
            if rule.get("last_triggered"):
                elapsed = (now - rule["last_triggered"]).total_seconds()
                if elapsed < rule.get("cooldown_seconds", 60):
                    continue

            pattern = rule.get("pattern", "*")
            change_type = rule.get("change_type", "any")

            for change in changes:
                rel_path = str(Path(change.path).relative_to(workspace)) if workspace.as_posix() in change.path else change.path

                type_match = change_type == "any" or change.change_type == change_type
                path_match = fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(Path(change.path).name, pattern)

                if type_match and path_match:
                    rule["last_triggered"] = now
                    await self._execute_trigger(rule, change)
                    break

    async def _execute_trigger(self, rule: Dict, change: FileChange):
        """Execute a triggered rule."""
        action = rule.get("action", "suggest")

        if action == "suggest":
            self._add_suggestion(
                id=f"trigger_{rule['name']}",
                type="trigger",
                title=rule.get("message", f"Rule triggered: {rule['name']}"),
                message=f"File change detected: {Path(change.path).name} ({change.change_type})",
                action="run_playbook",
            )
        elif action == "run_playbook":
            playbook_id = rule.get("playbook_id")
            if playbook_id:
                try:
                    from graphs.orchestrator import execute_playbook
                    asyncio.create_task(execute_playbook(playbook_id))
                    logger.info("trigger_executed", rule=rule["name"], playbook=playbook_id)
                except Exception as e:
                    logger.error("trigger_execution_failed", error=str(e))

    # ─── Briefing Helper ────────────────────────────────────────

    def _should_generate_briefing(self) -> bool:
        """Check if it's time for a new briefing."""
        if not self._last_briefing:
            return True
        elapsed = (datetime.utcnow() - self._last_briefing).total_seconds()
        return elapsed >= 86400  # Every 24 hours


# Singleton
daemon_service = DaemonService()
