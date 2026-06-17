"""Semantic Skills — Auto-activated skill injection based on input."""

from typing import Optional

import structlog

logger = structlog.get_logger()

# Built-in skill definitions
BUILT_IN_SKILLS = {
    "api_design": {
        "triggers": ["api", "endpoint", "rest", "graphql", "route", "http"],
        "instruction": "Follow RESTful conventions. Use proper HTTP methods. Include error handling. Document with OpenAPI.",
    },
    "error_handling": {
        "triggers": ["error", "exception", "try", "catch", "handle", "fail"],
        "instruction": "Use proper exception hierarchy. Log errors with context. Provide user-friendly messages. Never swallow exceptions silently.",
    },
    "testing": {
        "triggers": ["test", "unittest", "pytest", "coverage", "mock", "assert"],
        "instruction": "Write tests for edge cases. Use descriptive test names. Mock external dependencies. Aim for high coverage.",
    },
    "security": {
        "triggers": ["security", "auth", "permission", "encrypt", "sanitize", "inject"],
        "instruction": "Validate all inputs. Sanitize outputs. Use parameterized queries. Never expose secrets. Follow OWASP guidelines.",
    },
    "docker": {
        "triggers": ["docker", "container", "compose", "image", "dockerfile"],
        "instruction": "Use multi-stage builds. Pin image versions. Don't run as root. Minimize layer count. Use .dockerignore.",
    },
    "performance": {
        "triggers": ["performance", "optimize", "cache", "fast", "slow", "latency"],
        "instruction": "Profile before optimizing. Use appropriate data structures. Consider caching. Avoid premature optimization.",
    },
}


class SemanticSkills:
    """Auto-activate skills based on input content."""

    def __init__(self):
        self._threshold = 0.3  # Minimum relevance

    def get_relevant_skills(self, input_text: str) -> list[dict]:
        """Find skills relevant to the input."""
        input_lower = input_text.lower()
        input_words = set(input_lower.split())
        relevant = []

        for skill_name, skill_data in BUILT_IN_SKILLS.items():
            triggers = skill_data["triggers"]
            matches = sum(1 for t in triggers if t in input_lower)
            relevance = matches / len(triggers)

            if relevance >= self._threshold:
                relevant.append({
                    "name": skill_name,
                    "relevance": relevance,
                    "instruction": skill_data["instruction"],
                })

        return sorted(relevant, key=lambda x: x["relevance"], reverse=True)

    def get_skill_instructions(self, input_text: str) -> str:
        """Get formatted skill instructions for prompt injection."""
        skills = self.get_relevant_skills(input_text)
        if not skills:
            return ""

        parts = ["## Active Skills"]
        for skill in skills[:3]:  # Max 3 skills
            parts.append(f"**{skill['name']}**: {skill['instruction']}")

        return "\n".join(parts)


# Global instance
semantic_skills = SemanticSkills()
