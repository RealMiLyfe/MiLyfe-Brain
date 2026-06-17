"""MiLyfe Brain — Hierarchical .rules File Loading & Merging."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml
import structlog

from config import settings

logger = structlog.get_logger()


class RuleLoader:
    """Loads and merges .rules YAML files from the hierarchy.

    Cascade: system → ~/.milyfe/rules/ → <workspace>/.milyfe/rules/ → subdir
    Deep merge (later overrides earlier).
    """

    def __init__(self):
        self._rules: Dict[str, Any] = {}
        self.reload()

    def reload(self):
        """Reload rules from all directories."""
        self._rules = {}
        for rules_dir in settings.rules_dirs:
            if not rules_dir.exists():
                continue
            for rule_file in sorted(rules_dir.glob("*.yaml")):
                try:
                    data = yaml.safe_load(rule_file.read_text()) or {}
                    self._rules = self._deep_merge(self._rules, data)
                except Exception as e:
                    logger.warning("rule_load_error", file=str(rule_file), error=str(e))

            for rule_file in sorted(rules_dir.glob("*.yml")):
                try:
                    data = yaml.safe_load(rule_file.read_text()) or {}
                    self._rules = self._deep_merge(self._rules, data)
                except Exception as e:
                    logger.warning("rule_load_error", file=str(rule_file), error=str(e))

    def get_rules_for_prompt(self, role: str = None) -> str:
        """Get rules formatted for prompt injection."""
        parts = []

        # Global rules
        global_rules = self._rules.get("global", {})
        if global_rules:
            parts.append(self._format_section("Global Rules", global_rules))

        # Role-specific rules
        if role:
            role_rules = self._rules.get("roles", {}).get(role, {})
            if role_rules:
                parts.append(self._format_section(f"Rules for {role}", role_rules))

        # Coding standards
        standards = self._rules.get("standards", {})
        if standards:
            parts.append(self._format_section("Coding Standards", standards))

        return "\n\n".join(parts) if parts else ""

    def get(self, key: str, default: Any = None) -> Any:
        """Get a rule value by dot-notation."""
        parts = key.split(".")
        value = self._rules
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return default
        return value if value is not None else default

    def _format_section(self, title: str, data: Any) -> str:
        """Format a rules section for prompt."""
        if isinstance(data, dict):
            lines = [f"[{title}]"]
            for k, v in data.items():
                if isinstance(v, list):
                    lines.append(f"- {k}: {', '.join(str(i) for i in v)}")
                else:
                    lines.append(f"- {k}: {v}")
            return "\n".join(lines)
        elif isinstance(data, list):
            return f"[{title}]\n" + "\n".join(f"- {item}" for item in data)
        return f"[{title}] {data}"

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = RuleLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result


# Singleton
rule_loader = RuleLoader()
