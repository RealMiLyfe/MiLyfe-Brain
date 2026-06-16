"""Hierarchical .rules file merging.

Cascade: system → ~/.milyfe/rules/ → <workspace>/.milyfe/rules/ → <subdir>/.milyfe/rules/
Deep merge (later overrides earlier).
"""

import os
from pathlib import Path
from typing import Any

import yaml
import structlog

from config import settings

logger = structlog.get_logger()


class RuleLoader:
    """Load and merge rules from hierarchical sources."""

    def __init__(self):
        self._cache: dict[str, dict] = {}

    def load_rules(self, workspace_path: str = None) -> dict[str, Any]:
        """Load merged rules from all levels."""
        workspace = Path(workspace_path or settings.workspace_dir)
        merged = {}

        # Level 1: System defaults
        system_rules = self._load_level(Path(__file__).parent / "default_rules.yaml")
        merged = self._deep_merge(merged, system_rules)

        # Level 2: User-level rules
        user_rules_dir = Path.home() / ".milyfe" / "rules"
        if user_rules_dir.exists():
            for rule_file in user_rules_dir.glob("*.yaml"):
                user_rules = self._load_level(rule_file)
                merged = self._deep_merge(merged, user_rules)

        # Level 3: Workspace-level rules
        workspace_rules_dir = workspace / ".milyfe" / "rules"
        if workspace_rules_dir.exists():
            for rule_file in workspace_rules_dir.glob("*.yaml"):
                ws_rules = self._load_level(rule_file)
                merged = self._deep_merge(merged, ws_rules)

        return merged

    def get_prompt_additions(self, workspace_path: str = None) -> str:
        """Get formatted rules for injection into prompts."""
        rules = self.load_rules(workspace_path)

        if not rules:
            return ""

        parts = ["## Project Rules"]

        if "identity" in rules:
            parts.append(f"Identity: {rules['identity']}")
        if "tone" in rules:
            parts.append(f"Tone: {rules['tone']}")
        if "coding_standards" in rules:
            standards = rules["coding_standards"]
            if isinstance(standards, list):
                parts.append("Coding Standards:")
                for s in standards:
                    parts.append(f"  - {s}")
            elif isinstance(standards, dict):
                for k, v in standards.items():
                    parts.append(f"  {k}: {v}")

        if "custom_rules" in rules:
            parts.append("Custom Rules:")
            for rule in rules["custom_rules"]:
                parts.append(f"  - {rule}")

        return "\n".join(parts)

    def _load_level(self, path: Path) -> dict:
        """Load rules from a file."""
        if not path.exists():
            return {}
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.warning("Failed to load rules", path=str(path), error=str(e))
            return {}

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep merge two dictionaries (override wins)."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            elif key in result and isinstance(result[key], list) and isinstance(value, list):
                result[key] = result[key] + value
            else:
                result[key] = value
        return result


# Global instance
rule_loader = RuleLoader()
