"""PlaybookParser — Convert natural language / markdown / JSON into structured steps.

Uses httpx → Ollama for NL parsing.
"""

import json
import uuid
from typing import Optional

import httpx
import structlog

from config import settings

logger = structlog.get_logger()

PARSE_PROMPT = """You are a task decomposition expert. Given a user's goal description, break it down into concrete, actionable steps.

For each step, provide:
- id: a short unique identifier (e.g., "step_1")
- description: what needs to be done
- agent_role: which agent should handle it (orchestrator, researcher, coder, executor, critic, designer, writer, debugger, planner)
- depends_on: list of step IDs this step depends on (empty list if none)
- complexity: light, medium, or heavy
- tools_needed: list of tools needed (file_read, file_write, shell_exec, code_exec, web_browse, grep_search, glob_search, etc.)

Output ONLY valid JSON array of steps. No explanation.

Example output:
[
  {"id": "step_1", "description": "Research best practices for API design", "agent_role": "researcher", "depends_on": [], "complexity": "light", "tools_needed": ["web_search"]},
  {"id": "step_2", "description": "Design the API schema", "agent_role": "designer", "depends_on": ["step_1"], "complexity": "medium", "tools_needed": ["file_write"]},
  {"id": "step_3", "description": "Implement the API endpoints", "agent_role": "coder", "depends_on": ["step_2"], "complexity": "heavy", "tools_needed": ["file_write", "file_read"]}
]"""


class PlaybookParser:
    """Parse user input into structured playbook steps."""

    async def parse(self, raw_text: str, title: Optional[str] = None) -> list[dict]:
        """Parse raw text into structured steps.

        Supports:
        - Plain natural language
        - Markdown with bullet points
        - JSON array of steps (passed through)
        """
        # Try JSON first
        steps = self._try_json_parse(raw_text)
        if steps:
            return self._normalize_steps(steps)

        # Try markdown bullet parsing
        steps = self._try_markdown_parse(raw_text)
        if steps and len(steps) >= 2:
            return steps

        # Use LLM for natural language parsing
        steps = await self._llm_parse(raw_text)
        return steps

    def _try_json_parse(self, text: str) -> Optional[list[dict]]:
        """Try to parse as JSON array of steps."""
        text = text.strip()
        if text.startswith("["):
            try:
                data = json.loads(text)
                if isinstance(data, list) and len(data) > 0:
                    return data
            except json.JSONDecodeError:
                pass
        return None

    def _try_markdown_parse(self, text: str) -> Optional[list[dict]]:
        """Try to parse markdown bullet points as steps."""
        lines = text.strip().split("\n")
        steps = []
        step_num = 0

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match bullet points, numbered lists
            if line.startswith(("- ", "* ", "• ")) or (len(line) > 2 and line[0].isdigit() and line[1] in (".", ")")):
                step_num += 1
                # Remove bullet/number prefix
                if line[0].isdigit():
                    desc = line.split(" ", 1)[1] if " " in line else line
                else:
                    desc = line[2:]

                steps.append({
                    "id": f"step_{step_num}",
                    "description": desc.strip(),
                    "agent_role": self._infer_role(desc),
                    "depends_on": [f"step_{step_num - 1}"] if step_num > 1 else [],
                    "complexity": "medium",
                    "tools_needed": self._infer_tools(desc),
                })

        return steps if len(steps) >= 2 else None

    async def _llm_parse(self, text: str) -> list[dict]:
        """Use Ollama to parse natural language into steps."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json={
                        "model": settings.default_heavy_model,
                        "messages": [
                            {"role": "system", "content": PARSE_PROMPT},
                            {"role": "user", "content": text},
                        ],
                        "stream": False,
                        "options": {"temperature": 0.3},
                    },
                )
                resp.raise_for_status()
                content = resp.json().get("message", {}).get("content", "")

                # Extract JSON from response
                steps = self._extract_json_array(content)
                if steps:
                    return self._normalize_steps(steps)

        except Exception as e:
            logger.error("LLM parse failed", error=str(e))

        # Fallback: single step
        return [{
            "id": "step_1",
            "description": text[:500],
            "agent_role": "coder",
            "depends_on": [],
            "complexity": "medium",
            "tools_needed": ["file_write", "file_read"],
        }]

    def _extract_json_array(self, text: str) -> Optional[list]:
        """Extract JSON array from LLM output."""
        # Find array boundaries
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        return None

    def _normalize_steps(self, steps: list[dict]) -> list[dict]:
        """Ensure all steps have required fields."""
        normalized = []
        for i, step in enumerate(steps):
            normalized.append({
                "id": step.get("id", f"step_{i + 1}"),
                "description": step.get("description", "Unknown step"),
                "agent_role": step.get("agent_role", "coder"),
                "depends_on": step.get("depends_on", []),
                "complexity": step.get("complexity", "medium"),
                "tools_needed": step.get("tools_needed", []),
            })
        return normalized

    def _infer_role(self, description: str) -> str:
        """Infer agent role from step description."""
        desc_lower = description.lower()
        if any(w in desc_lower for w in ["research", "search", "find", "look up", "investigate"]):
            return "researcher"
        if any(w in desc_lower for w in ["write code", "implement", "create", "build", "develop"]):
            return "coder"
        if any(w in desc_lower for w in ["run", "execute", "deploy", "install", "setup"]):
            return "executor"
        if any(w in desc_lower for w in ["review", "test", "check", "validate", "verify"]):
            return "critic"
        if any(w in desc_lower for w in ["design", "architecture", "plan layout", "ui", "ux"]):
            return "designer"
        if any(w in desc_lower for w in ["document", "write doc", "readme", "report"]):
            return "writer"
        if any(w in desc_lower for w in ["debug", "fix", "diagnose", "error"]):
            return "debugger"
        if any(w in desc_lower for w in ["plan", "strategize", "organize", "prioritize"]):
            return "planner"
        return "coder"

    def _infer_tools(self, description: str) -> list[str]:
        """Infer tools needed from step description."""
        desc_lower = description.lower()
        tools = []
        if any(w in desc_lower for w in ["read", "examine", "look at"]):
            tools.append("file_read")
        if any(w in desc_lower for w in ["write", "create", "generate"]):
            tools.append("file_write")
        if any(w in desc_lower for w in ["run", "execute", "command", "install"]):
            tools.append("shell_exec")
        if any(w in desc_lower for w in ["search", "find", "browse"]):
            tools.append("web_search")
        if any(w in desc_lower for w in ["code", "script", "program"]):
            tools.append("code_exec")
        return tools or ["file_read"]


# Global instance
playbook_parser = PlaybookParser()
