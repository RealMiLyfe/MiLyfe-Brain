"""MiLyfe Brain — Semantic Skill Activation (auto-inject based on triggers)."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import structlog
import yaml

from config import settings

logger = structlog.get_logger()

# Built-in skills
BUILTIN_SKILLS = {
    "api_design": {
        "triggers": ["api", "endpoint", "rest", "route", "graphql", "http"],
        "instructions": "Follow RESTful conventions. Use proper HTTP methods. Version APIs. Include error responses. Document with OpenAPI.",
    },
    "error_handling": {
        "triggers": ["error", "exception", "try", "catch", "handle", "fail"],
        "instructions": "Use specific exception types. Never catch bare Exception in production. Log errors with context. Provide user-friendly messages.",
    },
    "testing": {
        "triggers": ["test", "spec", "assert", "mock", "pytest", "jest"],
        "instructions": "Write unit tests for edge cases. Use descriptive test names. Mock external dependencies. Aim for >80% coverage on critical paths.",
    },
    "security": {
        "triggers": ["auth", "password", "token", "secret", "encrypt", "sanitize", "xss", "sql injection"],
        "instructions": "Never store passwords in plaintext. Validate all inputs. Use parameterized queries. Sanitize outputs. Follow OWASP guidelines.",
    },
    "docker": {
        "triggers": ["docker", "container", "compose", "dockerfile", "image", "deploy"],
        "instructions": "Use multi-stage builds. Pin versions. Don't run as root. Use .dockerignore. Health checks required.",
    },
    "performance": {
        "triggers": ["performance", "optimize", "slow", "cache", "fast", "latency"],
        "instructions": "Profile before optimizing. Use caching strategically. Avoid N+1 queries. Lazy load where appropriate. Measure impact.",
    },
}


class SemanticSkills:
    """Auto-activates skills when input matches triggers."""

    def __init__(self):
        self._custom_skills: Dict[str, dict] = {}
        self._load_custom_skills()

    def _load_custom_skills(self):
        """Load custom skills from filesystem."""
        for skills_dir in settings.skills_dirs:
            if not skills_dir.exists():
                continue
            for skill_file in skills_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(skill_file.read_text())
                    if data and "triggers" in data:
                        name = skill_file.stem
                        self._custom_skills[name] = data
                except Exception:
                    continue

    def get_active_skills(self, input_text: str, threshold: float = 0.3) -> List[str]:
        """Get skills that should be activated for this input."""
        input_lower = input_text.lower()
        input_words = set(input_lower.split())
        active = []

        all_skills = {**BUILTIN_SKILLS, **self._custom_skills}

        for name, skill in all_skills.items():
            triggers = skill.get("triggers", [])
            if not triggers:
                continue

            # Calculate relevance
            matches = sum(1 for t in triggers if t in input_lower)
            relevance = matches / len(triggers) if triggers else 0

            if relevance >= threshold:
                active.append(name)

        return active

    def get_skill_instructions(self, skill_names: List[str]) -> str:
        """Get combined instructions for active skills."""
        all_skills = {**BUILTIN_SKILLS, **self._custom_skills}
        parts = []
        for name in skill_names:
            skill = all_skills.get(name)
            if skill:
                instructions = skill.get("instructions", "")
                if instructions:
                    parts.append(f"[{name}] {instructions}")
        return "\n".join(parts)


# Singleton
semantic_skills = SemanticSkills()
