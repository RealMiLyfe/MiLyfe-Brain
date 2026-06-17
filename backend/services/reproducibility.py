"""
MiLyfe Brain - Reproducibility Service

Enables deterministic playbook execution for CI/CD pipelines.
Supports exporting runs as CI configurations and diffing run outputs.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def create_deterministic_config(
    playbook_id: str,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create a deterministic execution configuration for a playbook.

    Locks model versions, seeds, and parameters to ensure reproducible runs.

    Args:
        playbook_id: ID of the playbook to configure.
        seed: Random seed (auto-generated if None).

    Returns:
        Dict with deterministic config parameters.
    """
    from config import settings

    if seed is None:
        seed = int(hashlib.md5(playbook_id.encode()).hexdigest()[:8], 16)

    config = {
        "playbook_id": playbook_id,
        "seed": seed,
        "temperature": 0.0,  # Deterministic sampling
        "models": {
            "light": settings.default_light_model,
            "heavy": settings.default_heavy_model,
            "premium": settings.premium_model,
        },
        "max_retries": 0,  # No retries for reproducibility
        "timeout": settings.agent_timeout,
        "created_at": datetime.utcnow().isoformat(),
        "config_hash": "",  # Will be computed
    }

    # Compute config hash for verification
    config_str = json.dumps(config, sort_keys=True)
    config["config_hash"] = hashlib.sha256(config_str.encode()).hexdigest()[:16]

    logger.info("Deterministic config created for playbook %s (seed=%d)", playbook_id, seed)
    return config


async def export_as_ci(
    playbook_id: str,
    ci_format: str = "github_actions",
) -> str:
    """
    Export a playbook execution as a CI pipeline configuration.

    Args:
        playbook_id: ID of the playbook to export.
        ci_format: Target format ('github_actions', 'gitlab_ci', 'makefile').

    Returns:
        CI configuration as a string.
    """
    try:
        from sqlalchemy import select

        from memory.database import PlaybookRow, PlaybookStepRow, async_session_factory

        if async_session_factory is None:
            return f"# Cannot export: database unavailable (playbook: {playbook_id})"

        async with async_session_factory() as session:
            pb_result = await session.execute(
                select(PlaybookRow).where(PlaybookRow.id == playbook_id)
            )
            playbook = pb_result.scalar_one_or_none()
            if playbook is None:
                return f"# Playbook not found: {playbook_id}"

            steps_result = await session.execute(
                select(PlaybookStepRow)
                .where(PlaybookStepRow.playbook_id == playbook_id)
                .order_by(PlaybookStepRow.order_num)
            )
            steps = steps_result.scalars().all()

        if ci_format == "github_actions":
            return _to_github_actions(playbook, steps)
        elif ci_format == "gitlab_ci":
            return _to_gitlab_ci(playbook, steps)
        else:
            return _to_makefile(playbook, steps)

    except Exception as e:
        logger.error("Failed to export as CI: %s", e)
        return f"# Export failed: {e}"


async def diff_runs(
    run_id_a: str,
    run_id_b: str,
) -> Dict[str, Any]:
    """
    Diff the outputs of two playbook runs.

    Args:
        run_id_a: First run/playbook ID.
        run_id_b: Second run/playbook ID.

    Returns:
        Dict with 'identical', 'differences' list.
    """
    # Stub: would compare step outputs between two runs
    logger.info("Diffing runs: %s vs %s", run_id_a, run_id_b)

    return {
        "identical": False,
        "run_a": run_id_a,
        "run_b": run_id_b,
        "differences": [
            {"step": "comparison not yet implemented", "type": "stub"},
        ],
    }


def _to_github_actions(playbook: Any, steps: List[Any]) -> str:
    """Convert playbook to GitHub Actions YAML."""
    lines = [
        f"# Auto-generated from MiLyfe Brain playbook: {playbook.title}",
        f"name: {playbook.title}",
        "on: [workflow_dispatch]",
        "jobs:",
        "  execute:",
        "    runs-on: ubuntu-latest",
        "    steps:",
        "      - uses: actions/checkout@v4",
    ]
    for step in steps:
        lines.append(f"      - name: {step.title}")
        lines.append(f"        run: echo 'Step: {step.title}'")
    return "\n".join(lines)


def _to_gitlab_ci(playbook: Any, steps: List[Any]) -> str:
    """Convert playbook to GitLab CI YAML."""
    lines = [
        f"# Auto-generated from MiLyfe Brain playbook: {playbook.title}",
        "stages:",
    ]
    for i, step in enumerate(steps):
        lines.append(f"  - step_{i}")
    lines.append("")
    for i, step in enumerate(steps):
        lines.append(f"step_{i}:")
        lines.append(f"  stage: step_{i}")
        lines.append(f"  script:")
        lines.append(f"    - echo '{step.title}'")
        lines.append("")
    return "\n".join(lines)


def _to_makefile(playbook: Any, steps: List[Any]) -> str:
    """Convert playbook to Makefile."""
    lines = [
        f"# Auto-generated from MiLyfe Brain playbook: {playbook.title}",
        ".PHONY: all " + " ".join(f"step_{i}" for i in range(len(steps))),
        "",
        "all: " + " ".join(f"step_{i}" for i in range(len(steps))),
        "",
    ]
    for i, step in enumerate(steps):
        lines.append(f"step_{i}:  # {step.title}")
        lines.append(f"\t@echo 'Executing: {step.title}'")
        lines.append("")
    return "\n".join(lines)
