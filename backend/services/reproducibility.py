"""MiLyfe Brain — Reproducibility / Deterministic Mode.

Seed locking, playbook versioning, run diffing, CI export.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from config import settings

logger = structlog.get_logger()


class ReproducibilityService:
    """Ensures reproducible playbook execution."""

    async def create_deterministic_config(self, playbook_id: str) -> Dict:
        """Create a deterministic execution config (temperature=0, fixed seed)."""
        seed = int(hashlib.md5(playbook_id.encode()).hexdigest()[:8], 16)
        return {
            "playbook_id": playbook_id,
            "seed": seed,
            "temperature": 0.0,
            "top_p": 1.0,
            "deterministic": True,
            "created_at": datetime.utcnow().isoformat(),
        }

    async def snapshot_run(self, playbook_id: str, run_data: Dict) -> str:
        """Save a complete run snapshot for later comparison."""
        snapshots_dir = Path(settings.workspace_dir) / ".runs"
        snapshots_dir.mkdir(parents=True, exist_ok=True)

        run_id = str(uuid.uuid4())[:8]
        snapshot = {
            "run_id": run_id,
            "playbook_id": playbook_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": run_data,
        }

        filepath = snapshots_dir / f"{playbook_id[:8]}_{run_id}.json"
        filepath.write_text(json.dumps(snapshot, indent=2, default=str))

        return run_id

    async def diff_runs(self, run_id_a: str, run_id_b: str) -> Dict:
        """Compare two runs of the same playbook side-by-side."""
        snapshots_dir = Path(settings.workspace_dir) / ".runs"

        run_a = self._find_run(snapshots_dir, run_id_a)
        run_b = self._find_run(snapshots_dir, run_id_b)

        if not run_a or not run_b:
            return {"error": "Run(s) not found"}

        # Compare steps
        steps_a = run_a.get("data", {}).get("steps", [])
        steps_b = run_b.get("data", {}).get("steps", [])

        diffs = []
        for i in range(max(len(steps_a), len(steps_b))):
            sa = steps_a[i] if i < len(steps_a) else None
            sb = steps_b[i] if i < len(steps_b) else None
            if sa != sb:
                diffs.append({
                    "step": i,
                    "run_a": sa,
                    "run_b": sb,
                    "changed": True,
                })

        return {
            "run_a": run_id_a,
            "run_b": run_id_b,
            "total_diffs": len(diffs),
            "diffs": diffs,
        }

    async def export_as_ci(self, playbook_id: str, format: str = "github_action") -> str:
        """Convert a playbook into a CI pipeline definition."""
        from memory.database import PlaybookRow, PlaybookStepRow, async_session_factory
        from sqlalchemy import select
        import orjson

        async with async_session_factory() as session:
            pb = await session.get(PlaybookRow, playbook_id)
            if not pb:
                raise ValueError("Playbook not found")

            steps_result = await session.execute(
                select(PlaybookStepRow)
                .where(PlaybookStepRow.playbook_id == playbook_id)
                .order_by(PlaybookStepRow.order_index)
            )
            steps = steps_result.scalars().all()

        if format == "github_action":
            return self._to_github_action(pb.title, steps)
        elif format == "makefile":
            return self._to_makefile(pb.title, steps)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _to_github_action(self, title: str, steps: list) -> str:
        """Convert to GitHub Actions YAML."""
        lines = [
            f"name: {title}",
            "on: [push, workflow_dispatch]",
            "jobs:",
            "  run:",
            "    runs-on: ubuntu-latest",
            "    steps:",
            "      - uses: actions/checkout@v4",
        ]
        for step in steps:
            lines.append(f"      - name: {step.description[:60]}")
            lines.append(f"        run: echo 'Step: {step.description[:40]}'")
        return "\n".join(lines)

    def _to_makefile(self, title: str, steps: list) -> str:
        """Convert to Makefile."""
        lines = [f"# {title}", ".PHONY: all " + " ".join(f"step{i}" for i in range(len(steps))), ""]
        lines.append("all: " + " ".join(f"step{i}" for i in range(len(steps))))
        for i, step in enumerate(steps):
            lines.append(f"\nstep{i}:")
            lines.append(f"\t@echo '{step.description[:60]}'")
        return "\n".join(lines)

    def _find_run(self, directory: Path, run_id: str) -> Optional[Dict]:
        """Find a run snapshot by ID."""
        for f in directory.glob("*.json"):
            if run_id in f.name:
                return json.loads(f.read_text())
        return None


# Singleton
reproducibility_service = ReproducibilityService()
