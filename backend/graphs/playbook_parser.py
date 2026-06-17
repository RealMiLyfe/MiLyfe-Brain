"""PlaybookParser — Parses natural language into structured playbook steps.

Supports:
- Plain text descriptions (sent to Ollama for parsing)
- Markdown lists (parsed locally)
- JSON input (pass-through)
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import List, Optional

import httpx

from config import settings
from models.schemas import PlaybookStep, AgentRole, TaskComplexity

logger = logging.getLogger(__name__)

# Keywords to infer agent roles from step descriptions
ROLE_KEYWORDS = {
    AgentRole.researcher: ["research", "find", "search", "look up", "investigate", "analyze"],
    AgentRole.coder: ["code", "implement", "write", "create file", "build", "develop", "program"],
    AgentRole.executor: ["run", "execute", "test", "deploy", "install", "compile"],
    AgentRole.critic: ["review", "check", "validate", "verify", "audit", "assess"],
    AgentRole.designer: ["design", "ui", "ux", "layout", "style", "component"],
    AgentRole.writer: ["document", "write doc", "readme", "explain", "describe"],
    AgentRole.debugger: ["debug", "fix", "troubleshoot", "diagnose", "patch"],
    AgentRole.planner: ["plan", "architect", "strategy", "roadmap", "outline"],
}


class PlaybookParser:
    """Parses raw text, markdown, or JSON into structured PlaybookStep lists.

    Uses Ollama for natural language parsing when the input is complex
    free-form text. Falls back to local parsing for simple formats.
    """

    def __init__(self) -> None:
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Lazy-initialized httpx client for Ollama."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=settings.ollama_base_url,
                timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0),
            )
        return self._http_client

    async def parse(self, raw_text: str) -> List[PlaybookStep]:
        """Parse raw text into structured PlaybookStep list.

        Strategy:
        1. If input is valid JSON array of steps, pass through
        2. If input is a markdown list, parse locally
        3. Otherwise, use Ollama to parse natural language

        Args:
            raw_text: The raw input text (NL, markdown, or JSON).

        Returns:
            List of PlaybookStep objects with inferred roles and dependencies.
        """
        raw_text = raw_text.strip()

        if not raw_text:
            return []

        # Try JSON pass-through
        steps = self._try_json_parse(raw_text)
        if steps is not None:
            return steps

        # Try markdown list parsing
        steps = self._try_markdown_parse(raw_text)
        if steps:
            return steps

        # Fall back to Ollama NL parsing
        return await self._parse_with_llm(raw_text)

    def _try_json_parse(self, raw_text: str) -> Optional[List[PlaybookStep]]:
        """Attempt to parse input as JSON array of steps."""
        try:
            data = json.loads(raw_text)
            if isinstance(data, list):
                steps = []
                for i, item in enumerate(data):
                    if isinstance(item, dict):
                        step = PlaybookStep(
                            id=item.get("id", str(uuid.uuid4())),
                            description=item.get("description", item.get("task", "")),
                            agent_role=self._parse_role(item.get("agent_role")),
                            depends_on=item.get("depends_on", []),
                            complexity=self._parse_complexity(item.get("complexity")),
                        )
                        steps.append(step)
                    elif isinstance(item, str):
                        steps.append(self._text_to_step(item, i))
                return steps
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return None

    def _try_markdown_parse(self, raw_text: str) -> Optional[List[PlaybookStep]]:
        """Attempt to parse input as a markdown list."""
        lines = raw_text.split("\n")
        list_pattern = re.compile(r"^\s*[-*+]\s+(.+)$|^\s*\d+[.)]\s+(.+)$")

        items: List[str] = []
        for line in lines:
            match = list_pattern.match(line)
            if match:
                text = match.group(1) or match.group(2)
                if text:
                    items.append(text.strip())

        if len(items) >= 2:
            steps = []
            for i, item in enumerate(items):
                steps.append(self._text_to_step(item, i))
            return self._infer_dependencies(steps)

        return None

    async def _parse_with_llm(self, raw_text: str) -> List[PlaybookStep]:
        """Use Ollama to parse natural language into steps."""
        prompt = (
            "Parse the following task description into a list of discrete steps.\n"
            "Return ONLY a JSON array where each item has:\n"
            '- "description": what to do\n'
            '- "agent_role": one of [researcher, coder, executor, critic, designer, writer, debugger, planner]\n'
            '- "depends_on": array of step indices (0-based) this step depends on\n'
            '- "complexity": one of [light, medium, heavy]\n\n'
            f"Task:\n{raw_text}\n\n"
            "JSON output:"
        )

        try:
            response = await self.http_client.post(
                "/api/generate",
                json={
                    "model": settings.default_light_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 2048},
                },
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("response", "")

            # Extract JSON from response
            json_match = re.search(r"\[.*\]", text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                steps = []
                for i, item in enumerate(parsed):
                    if isinstance(item, dict):
                        # Convert index-based depends_on to IDs
                        step_id = str(uuid.uuid4())
                        step = PlaybookStep(
                            id=step_id,
                            description=item.get("description", ""),
                            agent_role=self._parse_role(item.get("agent_role")),
                            complexity=self._parse_complexity(item.get("complexity")),
                            depends_on=[],
                        )
                        steps.append(step)

                # Resolve index-based dependencies to IDs
                for i, item in enumerate(parsed):
                    if isinstance(item, dict):
                        deps = item.get("depends_on", [])
                        if deps:
                            steps[i].depends_on = [
                                steps[int(d)].id
                                for d in deps
                                if isinstance(d, int) and 0 <= d < len(steps)
                            ]

                return steps

        except Exception as e:
            logger.warning("LLM parsing failed, falling back to simple split: %s", e)

        # Final fallback: split by sentences/lines
        sentences = [s.strip() for s in re.split(r"[.\n]", raw_text) if s.strip()]
        steps = [self._text_to_step(s, i) for i, s in enumerate(sentences)]
        return steps

    def _text_to_step(self, text: str, index: int) -> PlaybookStep:
        """Convert a single text string to a PlaybookStep with inferred role."""
        role = self._infer_role(text)
        complexity = self._infer_complexity(text)
        return PlaybookStep(
            id=str(uuid.uuid4()),
            description=text,
            agent_role=role,
            complexity=complexity,
            depends_on=[],
        )

    def _infer_role(self, text: str) -> Optional[AgentRole]:
        """Infer the agent role from keywords in the description."""
        text_lower = text.lower()
        for role, keywords in ROLE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return role
        return AgentRole.coder  # Default

    def _infer_complexity(self, text: str) -> TaskComplexity:
        """Infer complexity from text length and keywords."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["simple", "quick", "easy", "trivial", "small"]):
            return TaskComplexity.light
        if any(w in text_lower for w in ["complex", "advanced", "architect", "system", "large"]):
            return TaskComplexity.heavy
        return TaskComplexity.medium

    def _infer_dependencies(self, steps: List[PlaybookStep]) -> List[PlaybookStep]:
        """Infer sequential dependencies for a list of steps.

        Simple heuristic: each step depends on the previous one
        unless it appears independent.
        """
        for i in range(1, len(steps)):
            steps[i].depends_on = [steps[i - 1].id]
        return steps

    def _parse_role(self, value: Optional[str]) -> Optional[AgentRole]:
        """Safely parse a role string to AgentRole enum."""
        if not value:
            return None
        try:
            return AgentRole(value.lower())
        except ValueError:
            return None

    def _parse_complexity(self, value: Optional[str]) -> TaskComplexity:
        """Safely parse a complexity string."""
        if not value:
            return TaskComplexity.medium
        try:
            return TaskComplexity(value.lower())
        except ValueError:
            return TaskComplexity.medium


# Singleton
playbook_parser = PlaybookParser()
