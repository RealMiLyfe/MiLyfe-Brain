"""
MiLyfe Brain - CI Importer Service

Imports CI/CD configurations from various formats and converts them
into MiLyfe Brain playbooks.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def import_file(file_path: str) -> Dict[str, Any]:
    """
    Auto-detect and import a CI configuration file.

    Supports GitHub Actions, GitLab CI, Makefile, and Dockerfile.

    Args:
        file_path: Path to the CI config file.

    Returns:
        Dict with 'success', 'playbook_data', 'format_detected'.
    """
    path = Path(file_path)

    if not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    content = path.read_text(errors="ignore")
    filename = path.name.lower()

    # Auto-detect format
    if filename.endswith((".yml", ".yaml")) and ".github" in str(path):
        return await import_github_actions(content)
    elif filename == ".gitlab-ci.yml":
        return await import_gitlab_ci(content)
    elif filename == "makefile" or filename.endswith(".mk"):
        return await import_makefile(content)
    elif filename == "dockerfile":
        return await import_dockerfile(content)
    else:
        return {
            "success": False,
            "error": f"Unrecognized CI format: {filename}",
            "supported_formats": ["GitHub Actions", "GitLab CI", "Makefile", "Dockerfile"],
        }


async def import_github_actions(content: str) -> Dict[str, Any]:
    """
    Import a GitHub Actions workflow YAML.

    Args:
        content: YAML content of the workflow file.

    Returns:
        Dict with extracted steps as playbook data.
    """
    try:
        import yaml
        data = yaml.safe_load(content)
    except Exception:
        # Fallback: regex extraction
        data = None

    steps: List[Dict[str, str]] = []

    if data and isinstance(data, dict):
        jobs = data.get("jobs", {})
        for job_name, job_config in jobs.items():
            if isinstance(job_config, dict):
                job_steps = job_config.get("steps", [])
                for step in job_steps:
                    if isinstance(step, dict):
                        name = step.get("name", step.get("uses", "unnamed step"))
                        run_cmd = step.get("run", "")
                        steps.append({
                            "title": f"[{job_name}] {name}",
                            "description": run_cmd if run_cmd else f"Uses: {step.get('uses', '')}",
                            "agent_role": "executor",
                        })
    else:
        # Regex fallback
        for match in re.finditer(r"-\s+name:\s*(.+)", content):
            steps.append({
                "title": match.group(1).strip(),
                "description": "",
                "agent_role": "executor",
            })

    return {
        "success": True,
        "format_detected": "github_actions",
        "playbook_data": {
            "title": "Imported from GitHub Actions",
            "steps": steps,
        },
    }


async def import_makefile(content: str) -> Dict[str, Any]:
    """
    Import a Makefile into playbook steps.

    Args:
        content: Makefile content.

    Returns:
        Dict with extracted targets as playbook steps.
    """
    steps: List[Dict[str, str]] = []

    # Extract targets and their commands
    target_pattern = re.compile(r"^([a-zA-Z_][\w-]*):\s*(.*?)$", re.MULTILINE)
    for match in target_pattern.finditer(content):
        target_name = match.group(1)
        if target_name.startswith("."):
            continue  # Skip special targets like .PHONY

        # Find commands for this target (indented lines after target)
        pos = match.end()
        commands = []
        for line in content[pos:].split("\n"):
            if line.startswith("\t"):
                commands.append(line.strip())
            elif line.strip() == "":
                continue
            else:
                break

        steps.append({
            "title": f"make {target_name}",
            "description": "; ".join(commands) if commands else f"Run make target: {target_name}",
            "agent_role": "executor",
        })

    return {
        "success": True,
        "format_detected": "makefile",
        "playbook_data": {
            "title": "Imported from Makefile",
            "steps": steps,
        },
    }


async def import_dockerfile(content: str) -> Dict[str, Any]:
    """
    Import a Dockerfile into playbook steps.

    Args:
        content: Dockerfile content.

    Returns:
        Dict with extracted instructions as playbook steps.
    """
    steps: List[Dict[str, str]] = []

    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(None, 1)
        if len(parts) < 2:
            continue

        instruction = parts[0].upper()
        args = parts[1]

        if instruction in ("RUN", "COPY", "ADD", "WORKDIR", "ENV", "EXPOSE"):
            steps.append({
                "title": f"{instruction}: {args[:80]}",
                "description": line,
                "agent_role": "executor",
            })

    return {
        "success": True,
        "format_detected": "dockerfile",
        "playbook_data": {
            "title": "Imported from Dockerfile",
            "steps": steps,
        },
    }


async def import_gitlab_ci(content: str) -> Dict[str, Any]:
    """
    Import a GitLab CI YAML configuration.

    Args:
        content: YAML content of .gitlab-ci.yml.

    Returns:
        Dict with extracted jobs as playbook steps.
    """
    steps: List[Dict[str, str]] = []

    try:
        import yaml
        data = yaml.safe_load(content)
    except Exception:
        data = None

    if data and isinstance(data, dict):
        # Skip special keys
        special_keys = {"stages", "variables", "image", "services", "before_script", "after_script", "cache"}

        for job_name, job_config in data.items():
            if job_name in special_keys or job_name.startswith("."):
                continue

            if isinstance(job_config, dict):
                script = job_config.get("script", [])
                stage = job_config.get("stage", "default")

                description = "; ".join(script) if isinstance(script, list) else str(script)
                steps.append({
                    "title": f"[{stage}] {job_name}",
                    "description": description[:500],
                    "agent_role": "executor",
                })
    else:
        # Regex fallback for job names
        for match in re.finditer(r"^(\w[\w-]*):", content, re.MULTILINE):
            job_name = match.group(1)
            if job_name not in ("stages", "variables", "image", "services"):
                steps.append({
                    "title": job_name,
                    "description": "",
                    "agent_role": "executor",
                })

    return {
        "success": True,
        "format_detected": "gitlab_ci",
        "playbook_data": {
            "title": "Imported from GitLab CI",
            "steps": steps,
        },
    }
