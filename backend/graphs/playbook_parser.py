"""
MiLyfe Brain - Playbook Parser

Parses natural language, markdown, and JSON playbook descriptions into
structured PlaybookStep objects using a cascading strategy:
  1. Direct JSON parsing
  2. Markdown list extraction
  3. LLM-based decomposition via Ollama
"""
from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Optional
from uuid import uuid4

import httpx

from config import settings
from models.schemas import AgentRole, PlaybookStep, TaskComplexity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System Prompt for LLM-based Parsing
# ---------------------------------------------------------------------------

PARSE_SYSTEM_PROMPT = """You are a task decomposition engine. Given a goal or description, break it down into discrete executable steps.

Output ONLY a JSON array of objects. Each object must have:
- "title": short step title (< 80 chars)
- "description": detailed description of what to do
- "agent_role": one of "planner", "researcher", "coder", "executor", "reviewer", "writer", "browser", "gui", "orchestrator"
- "order": integer execution order starting at 1
- "dependencies": array of step orders this depends on (empty if none)

Rules:
- Steps should be atomic and independently verifiable.
- Assign the most appropriate agent role based on the task nature.
- Keep steps ordered logically. If steps can run in parallel, give them the same order number.
- Aim for 3-10 steps for most tasks.
- Output ONLY valid JSON. No markdown, no explanation, no code fences."""

# ---------------------------------------------------------------------------
# Keyword Maps for Inference
# ---------------------------------------------------------------------------

_ROLE_KEYWORDS: Dict[str, AgentRole] = {
    "research": AgentRole.RESEARCHER,
    "search": AgentRole.RESEARCHER,
    "find": AgentRole.RESEARCHER,
    "look up": AgentRole.RESEARCHER,
    "investigate": AgentRole.RESEARCHER,
    "gather": AgentRole.RESEARCHER,
    "code": AgentRole.CODER,
    "implement": AgentRole.CODER,
    "build": AgentRole.CODER,
    "write code": AgentRole.CODER,
    "develop": AgentRole.CODER,
    "program": AgentRole.CODER,
    "refactor": AgentRole.CODER,
    "fix bug": AgentRole.CODER,
    "debug": AgentRole.CODER,
    "run": AgentRole.EXECUTOR,
    "execute": AgentRole.EXECUTOR,
    "install": AgentRole.EXECUTOR,
    "deploy": AgentRole.EXECUTOR,
    "shell": AgentRole.EXECUTOR,
    "command": AgentRole.EXECUTOR,
    "test": AgentRole.EXECUTOR,
    "review": AgentRole.REVIEWER,
    "check": AgentRole.REVIEWER,
    "validate": AgentRole.REVIEWER,
    "verify": AgentRole.REVIEWER,
    "audit": AgentRole.REVIEWER,
    "inspect": AgentRole.REVIEWER,
    "plan": AgentRole.PLANNER,
    "design": AgentRole.PLANNER,
    "architect": AgentRole.PLANNER,
    "strategy": AgentRole.PLANNER,
    "outline": AgentRole.PLANNER,
    "write": AgentRole.WRITER,
    "document": AgentRole.WRITER,
    "documentation": AgentRole.WRITER,
    "readme": AgentRole.WRITER,
    "report": AgentRole.WRITER,
    "summarize": AgentRole.WRITER,
    "browse": AgentRole.BROWSER,
    "scrape": AgentRole.BROWSER,
    "website": AgentRole.BROWSER,
    "navigate": AgentRole.BROWSER,
    "gui": AgentRole.GUI,
    "interface": AgentRole.GUI,
    "click": AgentRole.GUI,
    "automate ui": AgentRole.GUI,
}

_COMPLEXITY_KEYWORDS: Dict[str, TaskComplexity] = {
    "simple": TaskComplexity.SIMPLE,
    "trivial": TaskComplexity.TRIVIAL,
    "easy": TaskComplexity.SIMPLE,
    "quick": TaskComplexity.SIMPLE,
    "complex": TaskComplexity.COMPLEX,
    "difficult": TaskComplexity.COMPLEX,
    "advanced": TaskComplexity.COMPLEX,
    "expert": TaskComplexity.EXPERT,
    "sophisticated": TaskComplexity.EXPERT,
    "multi-step": TaskComplexity.MODERATE,
    "moderate": TaskComplexity.MODERATE,
}

_ROLE_TOOL_MAP: Dict[AgentRole, List[str]] = {
    AgentRole.RESEARCHER: ["web_search", "read_file", "scratchpad"],
    AgentRole.CODER: ["write_file", "read_file", "shell_exec", "scratchpad"],
    AgentRole.EXECUTOR: ["shell_exec", "read_file", "write_file"],
    AgentRole.REVIEWER: ["read_file", "shell_exec", "scratchpad"],
    AgentRole.PLANNER: ["scratchpad", "read_file"],
    AgentRole.WRITER: ["write_file", "read_file", "scratchpad"],
    AgentRole.BROWSER: ["browser_navigate", "browser_extract", "scratchpad"],
    AgentRole.GUI: ["gui_click", "gui_type", "gui_screenshot"],
    AgentRole.ORCHESTRATOR: ["scratchpad"],
}

_TOOL_KEYWORDS: Dict[str, str] = {
    "file": "read_file",
    "read": "read_file",
    "write": "write_file",
    "create file": "write_file",
    "save": "write_file",
    "shell": "shell_exec",
    "terminal": "shell_exec",
    "command": "shell_exec",
    "run": "shell_exec",
    "search": "web_search",
    "browse": "browser_navigate",
    "scrape": "browser_extract",
    "screenshot": "gui_screenshot",
    "click": "gui_click",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_playbook(text: str, model: Optional[str] = None) -> List[PlaybookStep]:
    """
    Parse a natural language / markdown / JSON description into PlaybookStep objects.

    Attempts parsing strategies in order:
      1. Direct JSON parsing
      2. Markdown list extraction
      3. LLM-based decomposition

    Always returns at least a 1-step fallback.
    """
    text = text.strip()
    if not text:
        return [_fallback_step("Execute the requested task")]

    # Strategy 1: Try direct JSON parse
    result = _try_json_parse(text)
    if result:
        return result

    # Strategy 2: Try markdown list extraction
    result = _try_markdown_parse(text)
    if result:
        return result

    # Strategy 3: LLM-based parse (synchronous wrapper for async call)
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're already in an async context; use a thread to avoid deadlock
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, _llm_parse(text, model))
            try:
                result = future.result(timeout=settings.agent_timeout)
            except Exception:
                result = None
    else:
        try:
            result = asyncio.run(_llm_parse(text, model))
        except Exception:
            result = None

    if result:
        return result

    # Fallback: single step with the full text as description
    return [_fallback_step(text)]


# ---------------------------------------------------------------------------
# Parsing Strategies
# ---------------------------------------------------------------------------


def _try_json_parse(text: str) -> Optional[List[PlaybookStep]]:
    """
    Attempt direct JSON parsing of the text.

    Handles both raw JSON arrays and JSON wrapped in code fences.
    """
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last fence lines
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        return None

    if isinstance(data, list):
        return _convert_raw_steps(data)
    elif isinstance(data, dict) and "steps" in data:
        return _convert_raw_steps(data["steps"])

    return None


def _try_markdown_parse(text: str) -> Optional[List[PlaybookStep]]:
    """
    Extract steps from numbered lists or bullet lists in markdown.

    Supports:
      - Numbered lists: "1. Do something" or "1) Do something"
      - Bullet lists: "- Do something" or "* Do something"
    """
    steps: List[PlaybookStep] = []

    # Pattern for numbered lists: "1. text" or "1) text"
    numbered_pattern = re.compile(r"^\s*(\d+)[.)]\s+(.+)$", re.MULTILINE)
    numbered_matches = numbered_pattern.findall(text)

    if len(numbered_matches) >= 2:
        for order_str, description in numbered_matches:
            order = int(order_str)
            title = description.strip()[:80]
            role = _infer_role(description)
            complexity = _infer_complexity(description)
            tools = _infer_tools(description, role)

            steps.append(PlaybookStep(
                id=str(uuid4()),
                title=title,
                description=description.strip(),
                agent_role=role,
                order=order,
                dependencies=[],
            ))
        return steps if steps else None

    # Pattern for bullet lists: "- text" or "* text"
    bullet_pattern = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)
    bullet_matches = bullet_pattern.findall(text)

    if len(bullet_matches) >= 2:
        for idx, description in enumerate(bullet_matches, start=1):
            title = description.strip()[:80]
            role = _infer_role(description)

            steps.append(PlaybookStep(
                id=str(uuid4()),
                title=title,
                description=description.strip(),
                agent_role=role,
                order=idx,
                dependencies=[],
            ))
        return steps if steps else None

    return None


async def _llm_parse(text: str, model: Optional[str] = None) -> Optional[List[PlaybookStep]]:
    """
    Use Ollama to decompose the text into structured steps via PARSE_SYSTEM_PROMPT.

    Returns None on timeout or parse failure.
    """
    target_model = model or settings.default_light_model

    payload = {
        "model": target_model,
        "messages": [
            {"role": "system", "content": PARSE_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 2048,
        },
    }

    try:
        async with httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0),
        ) as client:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()

            data = response.json()
            content = data.get("message", {}).get("content", "")

            if not content:
                return None

            return _try_json_parse(content)

    except httpx.TimeoutException:
        logger.warning("LLM parse timed out for text: %s...", text[:100])
        return None
    except httpx.HTTPStatusError as e:
        logger.warning("LLM parse HTTP error %d: %s", e.response.status_code, str(e))
        return None
    except Exception as e:
        logger.error("LLM parse unexpected error: %s", str(e))
        return None


# ---------------------------------------------------------------------------
# Conversion Helpers
# ---------------------------------------------------------------------------


def _convert_raw_steps(data: list) -> Optional[List[PlaybookStep]]:
    """
    Convert a list of raw dicts (from JSON) into validated PlaybookStep objects.

    Returns None if the data is empty or entirely invalid.
    """
    if not data or not isinstance(data, list):
        return None

    steps: List[PlaybookStep] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            continue

        title = str(item.get("title", item.get("name", f"Step {idx + 1}")))[:80]
        description = str(item.get("description", item.get("desc", title)))

        # Parse agent role
        role_str = str(item.get("agent_role", item.get("role", ""))).lower().strip()
        try:
            role = AgentRole(role_str)
        except ValueError:
            role = _infer_role(description)

        # Parse order
        order = int(item.get("order", item.get("step", idx + 1)))

        # Parse dependencies
        raw_deps = item.get("dependencies", item.get("depends_on", []))
        if isinstance(raw_deps, list):
            dependencies = [str(d) for d in raw_deps]
        else:
            dependencies = []

        steps.append(PlaybookStep(
            id=str(uuid4()),
            title=title,
            description=description,
            agent_role=role,
            order=order,
            dependencies=dependencies,
        ))

    return steps if steps else None


# ---------------------------------------------------------------------------
# Inference Helpers
# ---------------------------------------------------------------------------


def _infer_role(description: str) -> AgentRole:
    """
    Infer the most appropriate agent role from keyword matching on the description.

    Falls back to ORCHESTRATOR if no keywords match.
    """
    desc_lower = description.lower()

    # Check multi-word keywords first (longer matches take priority)
    sorted_keywords = sorted(_ROLE_KEYWORDS.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in desc_lower:
            return _ROLE_KEYWORDS[keyword]

    return AgentRole.ORCHESTRATOR


def _infer_complexity(description: str) -> TaskComplexity:
    """
    Infer task complexity from keyword matching on the description.

    Falls back to MODERATE if no keywords match.
    """
    desc_lower = description.lower()

    for keyword, complexity in _COMPLEXITY_KEYWORDS.items():
        if keyword in desc_lower:
            return complexity

    # Heuristic: longer descriptions tend to indicate more complexity
    word_count = len(description.split())
    if word_count < 5:
        return TaskComplexity.SIMPLE
    elif word_count > 30:
        return TaskComplexity.COMPLEX

    return TaskComplexity.MODERATE


def _infer_tools(description: str, role: AgentRole) -> List[str]:
    """
    Infer which tools a step might need based on description keywords and role.

    Combines keyword-matched tools with default tools for the role.
    """
    desc_lower = description.lower()
    tools: List[str] = []

    # Check keyword-based tool inference
    for keyword, tool_name in _TOOL_KEYWORDS.items():
        if keyword in desc_lower and tool_name not in tools:
            tools.append(tool_name)

    # Add role-default tools that aren't already present
    role_defaults = _ROLE_TOOL_MAP.get(role, [])
    for tool_name in role_defaults:
        if tool_name not in tools:
            tools.append(tool_name)

    return tools


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


def _fallback_step(description: str) -> PlaybookStep:
    """Create a single fallback step when all parsing strategies fail."""
    role = _infer_role(description)
    return PlaybookStep(
        id=str(uuid4()),
        title=description[:80],
        description=description,
        agent_role=role,
        order=1,
        dependencies=[],
    )
