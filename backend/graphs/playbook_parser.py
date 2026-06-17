"""MiLyfe Brain — Playbook Parser (NL/MD/JSON → structured steps via httpx→Ollama)."""

from __future__ import annotations

import json
import re
import uuid
from typing import List, Optional

import httpx
import structlog

from config import settings
from models.schemas import AgentRole, PlaybookStep, TaskComplexity

logger = structlog.get_logger()

PARSE_SYSTEM_PROMPT = """You are a task decomposition expert. Given a user's goal description, break it into concrete execution steps.

Output ONLY valid JSON array. Each step must have:
- "id": unique string like "step_1", "step_2"
- "description": clear action description
- "agent_role": one of [orchestrator, researcher, coder, executor, critic, designer, writer, debugger, planner]
- "depends_on": array of step IDs this depends on ([] if none)
- "complexity": one of [light, medium, heavy]
- "tools_needed": array of tool names needed

Rules:
1. Break into 2-15 steps (not too granular, not too vague)
2. Identify parallelizable steps (independent = same depends_on or [])
3. Assign the MOST appropriate agent role
4. Think about dependencies — what must complete before what?
5. For coding tasks, include a critic/review step

Example output:
[
  {"id": "step_1", "description": "Research best practices for REST API design", "agent_role": "researcher", "depends_on": [], "complexity": "light", "tools_needed": ["web_search"]},
  {"id": "step_2", "description": "Write the FastAPI route handlers", "agent_role": "coder", "depends_on": ["step_1"], "complexity": "heavy", "tools_needed": ["file_write", "file_read"]},
  {"id": "step_3", "description": "Review code for security issues", "agent_role": "critic", "depends_on": ["step_2"], "complexity": "medium", "tools_needed": ["file_read", "grep_search"]}
]"""


async def parse_playbook(
    text: str,
    model: Optional[str] = None,
) -> List[PlaybookStep]:
    """Parse natural language / markdown / JSON into structured steps.

    Tries in order:
    1. Direct JSON parsing (if input is already JSON)
    2. Markdown extraction (numbered/bulleted lists)
    3. LLM-based parsing (Ollama)
    """
    text = text.strip()

    # 1. Try direct JSON
    steps = _try_json_parse(text)
    if steps:
        logger.info("playbook_parsed", method="json", step_count=len(steps))
        return steps

    # 2. Try markdown extraction
    steps = _try_markdown_parse(text)
    if steps and len(steps) >= 2:
        logger.info("playbook_parsed", method="markdown", step_count=len(steps))
        return steps

    # 3. Use LLM to parse
    steps = await _llm_parse(text, model)
    if steps:
        logger.info("playbook_parsed", method="llm", step_count=len(steps))
        return steps

    # Fallback: single step
    logger.warning("playbook_parse_fallback", text_preview=text[:100])
    return [PlaybookStep(
        id="step_1",
        description=text[:500],
        agent_role=AgentRole.CODER,
        depends_on=[],
        complexity=TaskComplexity.MEDIUM,
        tools_needed=["file_write", "shell_exec"],
    )]


def _try_json_parse(text: str) -> List[PlaybookStep] | None:
    """Try parsing as JSON array of steps."""
    # Check if it looks like JSON
    if not (text.startswith("[") or text.startswith("{")):
        return None

    try:
        data = json.loads(text)
        if isinstance(data, dict) and "steps" in data:
            data = data["steps"]
        if not isinstance(data, list):
            return None

        return _convert_raw_steps(data)
    except json.JSONDecodeError:
        return None


def _try_markdown_parse(text: str) -> List[PlaybookStep] | None:
    """Extract steps from markdown lists."""
    steps = []

    # Match numbered lists: 1. Do something, 2. Do another thing
    numbered = re.findall(r"^\s*(\d+)[.)]\s*(.+)$", text, re.MULTILINE)
    if numbered:
        for i, (_, desc) in enumerate(numbered):
            role = _infer_role(desc)
            steps.append(PlaybookStep(
                id=f"step_{i+1}",
                description=desc.strip(),
                agent_role=role,
                depends_on=[f"step_{i}"] if i > 0 else [],
                complexity=_infer_complexity(desc),
                tools_needed=_infer_tools(desc, role),
            ))
        return steps if len(steps) >= 2 else None

    # Match bullet lists: - Do something
    bullets = re.findall(r"^\s*[-*]\s+(.+)$", text, re.MULTILINE)
    if bullets and len(bullets) >= 2:
        for i, desc in enumerate(bullets):
            role = _infer_role(desc)
            steps.append(PlaybookStep(
                id=f"step_{i+1}",
                description=desc.strip(),
                agent_role=role,
                depends_on=[f"step_{i}"] if i > 0 else [],
                complexity=_infer_complexity(desc),
                tools_needed=_infer_tools(desc, role),
            ))
        return steps

    return None


async def _llm_parse(text: str, model: Optional[str]) -> List[PlaybookStep] | None:
    """Use Ollama to parse natural language into steps."""
    model = model or settings.default_heavy_model

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
            )

            if resp.status_code != 200:
                logger.error("llm_parse_failed", status=resp.status_code)
                return None

            content = resp.json().get("message", {}).get("content", "")

            # Extract JSON from response
            json_match = re.search(r"\[[\s\S]*\]", content)
            if not json_match:
                return None

            data = json.loads(json_match.group())
            return _convert_raw_steps(data)

    except Exception as e:
        logger.error("llm_parse_error", error=str(e))
        return None


def _convert_raw_steps(data: list) -> List[PlaybookStep] | None:
    """Convert raw JSON data to PlaybookStep objects."""
    steps = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            role_str = item.get("agent_role", "coder")
            role = AgentRole(role_str) if role_str in [r.value for r in AgentRole] else AgentRole.CODER

            complexity_str = item.get("complexity", "medium")
            complexity = TaskComplexity(complexity_str) if complexity_str in [c.value for c in TaskComplexity] else TaskComplexity.MEDIUM

            steps.append(PlaybookStep(
                id=item.get("id", f"step_{len(steps)+1}"),
                description=item.get("description", ""),
                agent_role=role,
                depends_on=item.get("depends_on", []),
                complexity=complexity,
                tools_needed=item.get("tools_needed", []),
            ))
        except Exception:
            continue

    return steps if steps else None


def _infer_role(description: str) -> AgentRole:
    """Infer agent role from step description."""
    desc_lower = description.lower()

    if any(w in desc_lower for w in ["research", "search", "find", "look up", "investigate"]):
        return AgentRole.RESEARCHER
    if any(w in desc_lower for w in ["write code", "implement", "create function", "build", "develop"]):
        return AgentRole.CODER
    if any(w in desc_lower for w in ["run", "execute", "install", "deploy", "command", "shell"]):
        return AgentRole.EXECUTOR
    if any(w in desc_lower for w in ["review", "test", "check", "verify", "validate"]):
        return AgentRole.CRITIC
    if any(w in desc_lower for w in ["design", "architect", "plan layout", "ui", "ux"]):
        return AgentRole.DESIGNER
    if any(w in desc_lower for w in ["write doc", "readme", "document", "report", "summarize"]):
        return AgentRole.WRITER
    if any(w in desc_lower for w in ["debug", "fix", "diagnose", "troubleshoot"]):
        return AgentRole.DEBUGGER
    if any(w in desc_lower for w in ["plan", "break down", "decompose", "strategize"]):
        return AgentRole.PLANNER

    return AgentRole.CODER


def _infer_complexity(description: str) -> TaskComplexity:
    """Infer task complexity from description."""
    desc_lower = description.lower()
    if any(w in desc_lower for w in ["simple", "quick", "list", "check", "read"]):
        return TaskComplexity.LIGHT
    if any(w in desc_lower for w in ["complex", "full", "complete", "comprehensive", "entire"]):
        return TaskComplexity.HEAVY
    return TaskComplexity.MEDIUM


def _infer_tools(description: str, role: AgentRole) -> List[str]:
    """Infer tools needed based on description and role."""
    tools = []
    desc_lower = description.lower()

    if any(w in desc_lower for w in ["file", "read", "write", "create"]):
        tools.extend(["file_read", "file_write"])
    if any(w in desc_lower for w in ["search", "find", "look"]):
        tools.append("grep_search")
    if any(w in desc_lower for w in ["run", "execute", "install", "command"]):
        tools.append("shell_exec")
    if any(w in desc_lower for w in ["web", "browse", "url"]):
        tools.append("web_browse")
    if any(w in desc_lower for w in ["code", "script", "python"]):
        tools.append("code_exec")

    if not tools:
        role_defaults = {
            AgentRole.RESEARCHER: ["web_search", "file_read"],
            AgentRole.CODER: ["file_read", "file_write"],
            AgentRole.EXECUTOR: ["shell_exec", "file_write"],
            AgentRole.CRITIC: ["file_read", "grep_search"],
            AgentRole.WRITER: ["file_read", "file_write"],
            AgentRole.DEBUGGER: ["file_read", "grep_search", "code_exec"],
        }
        tools = role_defaults.get(role, ["file_read"])

    return tools
