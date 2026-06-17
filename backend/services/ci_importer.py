"""MiLyfe Brain — Import from CI/CD Configurations.

Parse GitHub Actions, Makefile, Dockerfile, and shell scripts
into MiLyfe Brain playbook steps.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
import yaml

from models.schemas import AgentRole, PlaybookStep, TaskComplexity

logger = structlog.get_logger()


class CIImporter:
    """Import CI/CD configurations as playbook steps."""

    async def import_file(self, path: str, content: Optional[str] = None) -> Dict:
        """Auto-detect file type and import."""
        if content is None:
            file_path = Path(path)
            if not file_path.exists():
                return {"error": f"File not found: {path}"}
            content = file_path.read_text()

        filename = Path(path).name.lower()

        if filename in (".github/workflows", "") or filename.endswith((".yml", ".yaml")):
            if "jobs:" in content and ("on:" in content or "name:" in content):
                return await self.import_github_actions(content, path)

        if filename == "makefile" or filename.endswith("makefile"):
            return await self.import_makefile(content, path)

        if filename == "dockerfile":
            return await self.import_dockerfile(content, path)

        if filename.endswith(".sh") or filename.endswith(".bash"):
            return await self.import_shell_script(content, path)

        if filename == "jenkinsfile":
            return await self.import_jenkinsfile(content, path)

        # Try auto-detection from content
        if "jobs:" in content and "runs-on:" in content:
            return await self.import_github_actions(content, path)
        if content.startswith("FROM "):
            return await self.import_dockerfile(content, path)
        if ".PHONY:" in content or re.search(r"^\w+:", content, re.MULTILINE):
            return await self.import_makefile(content, path)

        return {"error": f"Could not detect CI format for: {path}"}

    # ─── GitHub Actions ─────────────────────────────────────────

    async def import_github_actions(self, content: str, source: str = "") -> Dict:
        """Parse GitHub Actions YAML into playbook steps."""
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            return {"error": f"Invalid YAML: {e}"}

        if not isinstance(data, dict) or "jobs" not in data:
            return {"error": "Not a valid GitHub Actions workflow (missing 'jobs')"}

        workflow_name = data.get("name", "Imported Workflow")
        jobs = data.get("jobs", {})
        steps: List[PlaybookStep] = []
        job_ids: List[str] = []

        for job_name, job_config in jobs.items():
            if not isinstance(job_config, dict):
                continue

            job_steps = job_config.get("steps", [])
            needs = job_config.get("needs", [])
            if isinstance(needs, str):
                needs = [needs]

            # Map job dependencies to step dependencies
            job_depends = [f"job_{n}" for n in needs if f"job_{n}" in job_ids]

            for i, step_config in enumerate(job_steps):
                if not isinstance(step_config, dict):
                    continue

                step_name = step_config.get("name", f"{job_name}_step_{i}")
                step_id = f"job_{job_name}_{i}"

                # Determine what the step does
                if "uses" in step_config:
                    desc = f"Use action: {step_config['uses']}"
                    role = AgentRole.EXECUTOR
                    complexity = TaskComplexity.LIGHT
                elif "run" in step_config:
                    desc = f"Run: {step_config['run'][:200]}"
                    role = self._infer_role_from_command(step_config["run"])
                    complexity = self._infer_complexity_from_command(step_config["run"])
                else:
                    desc = step_name
                    role = AgentRole.EXECUTOR
                    complexity = TaskComplexity.LIGHT

                # Use step name if available
                if step_config.get("name"):
                    desc = f"{step_config['name']}: {desc}"

                depends = job_depends if i == 0 else [f"job_{job_name}_{i-1}"]

                steps.append(PlaybookStep(
                    id=step_id,
                    description=desc[:500],
                    agent_role=role,
                    depends_on=depends,
                    complexity=complexity,
                    tools_needed=self._infer_tools_from_command(step_config.get("run", "")),
                ))

            job_ids.append(f"job_{job_name}")

        return {
            "title": workflow_name,
            "description": f"Imported from GitHub Actions: {source or 'workflow'}",
            "source_type": "github_actions",
            "source_file": source,
            "steps": [s.model_dump() for s in steps],
            "step_count": len(steps),
        }

    # ─── Makefile ───────────────────────────────────────────────

    async def import_makefile(self, content: str, source: str = "") -> Dict:
        """Parse Makefile targets into playbook steps."""
        steps: List[PlaybookStep] = []

        # Parse targets and their commands
        targets: List[Dict] = []
        current_target: Optional[Dict] = None

        for line in content.split("\n"):
            # Skip comments and empty lines
            if line.startswith("#") or not line.strip():
                if current_target and line.startswith("# "):
                    current_target["description"] = line[2:].strip()
                continue

            # Target definition
            target_match = re.match(r"^([\w.-]+)\s*:(.*)$", line)
            if target_match and not line.startswith("\t"):
                if current_target:
                    targets.append(current_target)
                name = target_match.group(1)
                deps_str = target_match.group(2).strip()
                deps = [d.strip() for d in deps_str.split() if d.strip()] if deps_str else []
                current_target = {"name": name, "deps": deps, "commands": [], "description": ""}
            elif line.startswith("\t") and current_target:
                cmd = line.strip()
                if cmd and not cmd.startswith("@echo"):
                    current_target["commands"].append(cmd.lstrip("@"))

        if current_target:
            targets.append(current_target)

        # Skip .PHONY declarations
        targets = [t for t in targets if t["name"] != ".PHONY"]

        # Convert to steps
        target_ids = {t["name"]: f"make_{t['name']}" for t in targets}

        for t in targets:
            desc = t.get("description") or f"make {t['name']}"
            if t["commands"]:
                desc += f" ({'; '.join(t['commands'][:3])})"

            depends = [target_ids[d] for d in t["deps"] if d in target_ids]

            role = AgentRole.EXECUTOR
            complexity = TaskComplexity.MEDIUM
            if t["commands"]:
                role = self._infer_role_from_command(" ".join(t["commands"]))
                complexity = self._infer_complexity_from_command(" ".join(t["commands"]))

            steps.append(PlaybookStep(
                id=target_ids[t["name"]],
                description=desc[:500],
                agent_role=role,
                depends_on=depends,
                complexity=complexity,
                tools_needed=["shell_exec"],
            ))

        return {
            "title": f"Makefile: {source or 'imported'}",
            "description": f"Imported from Makefile with {len(targets)} targets",
            "source_type": "makefile",
            "source_file": source,
            "steps": [s.model_dump() for s in steps],
            "step_count": len(steps),
        }

    # ─── Dockerfile ─────────────────────────────────────────────

    async def import_dockerfile(self, content: str, source: str = "") -> Dict:
        """Parse Dockerfile instructions into playbook steps."""
        steps: List[PlaybookStep] = []
        step_idx = 0

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            instruction_match = re.match(r"^(\w+)\s+(.+)$", line)
            if not instruction_match:
                continue

            instruction = instruction_match.group(1).upper()
            args = instruction_match.group(2)

            if instruction == "FROM":
                steps.append(PlaybookStep(
                    id=f"docker_{step_idx}",
                    description=f"Set base image: {args}",
                    agent_role=AgentRole.EXECUTOR,
                    depends_on=[f"docker_{step_idx-1}"] if step_idx > 0 else [],
                    complexity=TaskComplexity.LIGHT,
                    tools_needed=["shell_exec"],
                ))
            elif instruction == "RUN":
                steps.append(PlaybookStep(
                    id=f"docker_{step_idx}",
                    description=f"Execute: {args[:200]}",
                    agent_role=self._infer_role_from_command(args),
                    depends_on=[f"docker_{step_idx-1}"] if step_idx > 0 else [],
                    complexity=self._infer_complexity_from_command(args),
                    tools_needed=["shell_exec"],
                ))
            elif instruction == "COPY":
                steps.append(PlaybookStep(
                    id=f"docker_{step_idx}",
                    description=f"Copy files: {args}",
                    agent_role=AgentRole.EXECUTOR,
                    depends_on=[f"docker_{step_idx-1}"] if step_idx > 0 else [],
                    complexity=TaskComplexity.LIGHT,
                    tools_needed=["file_write"],
                ))
            elif instruction in ("CMD", "ENTRYPOINT"):
                steps.append(PlaybookStep(
                    id=f"docker_{step_idx}",
                    description=f"Set {instruction.lower()}: {args}",
                    agent_role=AgentRole.EXECUTOR,
                    depends_on=[f"docker_{step_idx-1}"] if step_idx > 0 else [],
                    complexity=TaskComplexity.LIGHT,
                    tools_needed=["shell_exec"],
                ))
            else:
                continue  # Skip WORKDIR, ENV, EXPOSE, etc.

            step_idx += 1

        return {
            "title": f"Dockerfile: {source or 'imported'}",
            "description": f"Imported from Dockerfile with {len(steps)} build steps",
            "source_type": "dockerfile",
            "source_file": source,
            "steps": [s.model_dump() for s in steps],
            "step_count": len(steps),
        }

    # ─── Shell Script ───────────────────────────────────────────

    async def import_shell_script(self, content: str, source: str = "") -> Dict:
        """Parse shell script into playbook steps."""
        steps: List[PlaybookStep] = []
        step_idx = 0
        current_comment = ""

        for line in content.split("\n"):
            line = line.strip()

            # Skip shebang and empty lines
            if line.startswith("#!") or not line:
                continue

            # Track comments as descriptions for next command
            if line.startswith("#"):
                current_comment = line[1:].strip()
                continue

            # Skip variable assignments without commands
            if re.match(r"^\w+=", line) and "$()" not in line:
                continue

            desc = current_comment or f"Run: {line[:100]}"
            current_comment = ""

            steps.append(PlaybookStep(
                id=f"sh_{step_idx}",
                description=desc,
                agent_role=self._infer_role_from_command(line),
                depends_on=[f"sh_{step_idx-1}"] if step_idx > 0 else [],
                complexity=self._infer_complexity_from_command(line),
                tools_needed=["shell_exec"],
            ))
            step_idx += 1

        return {
            "title": f"Script: {source or 'imported'}",
            "description": f"Imported from shell script with {len(steps)} commands",
            "source_type": "shell_script",
            "source_file": source,
            "steps": [s.model_dump() for s in steps],
            "step_count": len(steps),
        }

    # ─── Jenkinsfile (basic) ────────────────────────────────────

    async def import_jenkinsfile(self, content: str, source: str = "") -> Dict:
        """Basic Jenkinsfile parser (stage-level)."""
        steps: List[PlaybookStep] = []
        step_idx = 0

        # Find stages
        stage_pattern = re.compile(r"stage\s*\(\s*['\"](.+?)['\"]\s*\)", re.MULTILINE)
        stages = stage_pattern.findall(content)

        for stage_name in stages:
            steps.append(PlaybookStep(
                id=f"jenkins_{step_idx}",
                description=f"Stage: {stage_name}",
                agent_role=AgentRole.EXECUTOR,
                depends_on=[f"jenkins_{step_idx-1}"] if step_idx > 0 else [],
                complexity=TaskComplexity.MEDIUM,
                tools_needed=["shell_exec"],
            ))
            step_idx += 1

        return {
            "title": f"Jenkinsfile: {source or 'imported'}",
            "description": f"Imported from Jenkinsfile with {len(steps)} stages",
            "source_type": "jenkinsfile",
            "source_file": source,
            "steps": [s.model_dump() for s in steps],
            "step_count": len(steps),
        }

    # ─── Helpers ────────────────────────────────────────────────

    def _infer_role_from_command(self, cmd: str) -> AgentRole:
        """Infer agent role from a command string."""
        cmd_lower = cmd.lower()
        if any(w in cmd_lower for w in ["test", "pytest", "jest", "spec", "lint", "check"]):
            return AgentRole.CRITIC
        if any(w in cmd_lower for w in ["build", "compile", "webpack", "tsc"]):
            return AgentRole.CODER
        if any(w in cmd_lower for w in ["deploy", "push", "publish", "release"]):
            return AgentRole.EXECUTOR
        if any(w in cmd_lower for w in ["install", "apt", "pip", "npm", "yarn"]):
            return AgentRole.EXECUTOR
        return AgentRole.EXECUTOR

    def _infer_complexity_from_command(self, cmd: str) -> TaskComplexity:
        """Infer complexity from command."""
        cmd_lower = cmd.lower()
        if any(w in cmd_lower for w in ["build", "compile", "test", "deploy"]):
            return TaskComplexity.HEAVY
        if any(w in cmd_lower for w in ["install", "copy", "mkdir"]):
            return TaskComplexity.LIGHT
        return TaskComplexity.MEDIUM

    def _infer_tools_from_command(self, cmd: str) -> List[str]:
        """Infer needed tools from command."""
        if not cmd:
            return ["shell_exec"]
        tools = ["shell_exec"]
        cmd_lower = cmd.lower()
        if any(w in cmd_lower for w in ["cat", "echo", "write", ">"]):
            tools.append("file_write")
        if any(w in cmd_lower for w in ["python", "node", "ruby"]):
            tools.append("code_exec")
        return tools


# Singleton
ci_importer = CIImporter()
