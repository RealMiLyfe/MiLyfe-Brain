"""Base agent with think/act loop using Ollama via httpx.

Provides the abstract foundation for all specialized agents.
No langchain-ollama dependency — pure httpx to Ollama /api/chat.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from config import settings
from agents.message_bus import Message, Topic, get_message_bus
from agents.tool_parser import ToolCall, parse_tool_calls

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent lifecycle states."""

    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"
    RETIRED = "retired"


class AgentRole(str, Enum):
    """Available agent roles."""

    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    CODER = "coder"
    EXECUTOR = "executor"
    CRITIC = "critic"
    DESIGNER = "designer"
    WRITER = "writer"
    DEBUGGER = "debugger"
    PLANNER = "planner"


@dataclass
class Thought:
    """A single thought in the agent's reasoning chain."""

    content: str
    timestamp: float = field(default_factory=time.time)
    tool_calls: List[ToolCall] = field(default_factory=list)
    tool_results: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AgentState:
    """Serializable snapshot of agent state."""

    id: str
    role: str
    name: str
    status: str
    model: str
    actions_taken: int
    thoughts_count: int
    created_at: float
    last_active: float


class BaseAgent(ABC):
    """Abstract base agent with think/act loop.

    Subclasses must define:
    - SYSTEM_PROMPT: class variable with the role's system prompt
    - preferred_model: class variable with the default model name

    The think/act loop:
    1. Build messages (system prompt + context + task)
    2. Call LLM via Ollama /api/chat
    3. Parse tool calls from response
    4. Execute tools (max 3 rounds per think() call)
    5. Store results in vector memory
    6. Post status updates to message bus
    """

    SYSTEM_PROMPT: str = "You are a helpful AI agent."
    preferred_model: str = settings.default_heavy_model

    # Maximum tool execution rounds per think() invocation
    MAX_TOOL_ROUNDS: int = 3

    def __init__(
        self,
        role: AgentRole,
        name: Optional[str] = None,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.role: AgentRole = role
        self.name: str = name or f"{role.value}-{self.id[:8]}"
        self.model: str = model or self.preferred_model
        self.status: AgentStatus = AgentStatus.IDLE
        self.tools: List[Dict[str, Any]] = tools or []
        self.context: Dict[str, Any] = context or {}

        # State tracking
        self.thoughts: List[Thought] = []
        self.actions_taken: int = 0
        self.created_at: float = time.time()
        self.last_active: float = time.time()

        # HTTP client for Ollama
        self._http_client: Optional[httpx.AsyncClient] = None

        # Message bus reference
        self._bus = get_message_bus()

        logger.info(
            "Agent created: %s (role=%s, model=%s)", self.name, self.role.value, self.model
        )

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Lazy-initialized httpx client for Ollama API calls."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=settings.ollama_base_url,
                timeout=httpx.Timeout(
                    connect=10.0,
                    read=120.0,
                    write=10.0,
                    pool=10.0,
                ),
            )
        return self._http_client

    def _build_system_prompt(self) -> str:
        """Build the full system prompt from components.

        Combines: role definition + rules + skills + environment snapshot.
        """
        parts = [self.SYSTEM_PROMPT]

        # Add available tools description
        if self.tools:
            tool_desc = "\n\n## Available Tools\n"
            for tool in self.tools:
                tool_name = tool.get("name", "unknown")
                tool_description = tool.get("description", "")
                tool_params = tool.get("parameters", {})
                tool_desc += f"\n### {tool_name}\n{tool_description}\n"
                if tool_params:
                    tool_desc += f"Parameters: {tool_params}\n"
            parts.append(tool_desc)

        # Add tool calling instructions
        if self.tools:
            parts.append(
                "\n\n## Tool Calling Format\n"
                "When you need to use a tool, respond with a JSON code block:\n"
                "```json\n"
                '{"name": "tool_name", "arguments": {"param": "value"}}\n'
                "```\n"
                "Wait for the tool result before continuing.\n"
                "You may call multiple tools in sequence (max 3 rounds per task)."
            )

        # Add environment context
        if self.context:
            env_desc = "\n\n## Current Context\n"
            for key, value in self.context.items():
                env_desc += f"- {key}: {value}\n"
            parts.append(env_desc)

        return "\n".join(parts)

    async def think(self, task: str) -> str:
        """Execute the think/act loop for a given task.

        Args:
            task: The task description or user message.

        Returns:
            Final response text after all tool rounds complete.
        """
        self.status = AgentStatus.THINKING
        self.last_active = time.time()

        # Recall relevant context from vector memory (ChromaDB)
        recall_context = ""
        try:
            from memory.vector_store import vector_store
            if vector_store.is_available:
                results = await vector_store.query(
                    collection_name=f"agent_{self.role.value}",
                    query_texts=[task[:500]],
                    n_results=3,
                )
                if results and results[0].get("documents"):
                    docs = results[0]["documents"]
                    if docs:
                        recall_context = "\n\n## Relevant Past Context\n" + "\n---\n".join(
                            doc[:300] for doc in docs if doc
                        )
        except Exception as e:
            logger.debug("Vector recall failed (non-fatal): %s", e)

        # Build initial messages
        system_prompt = self._build_system_prompt()
        if recall_context:
            system_prompt += recall_context

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task},
        ]

        # Add previous thought context (last 3 thoughts for continuity)
        if self.thoughts:
            recent = self.thoughts[-3:]
            for thought in recent:
                messages.insert(-1, {"role": "assistant", "content": thought.content})

        final_response = ""
        round_count = 0

        try:
            while round_count < self.MAX_TOOL_ROUNDS:
                round_count += 1

                # Call LLM
                response_text = await self._call_llm(messages)

                # Parse tool calls from response
                tool_calls = parse_tool_calls(response_text)

                # Create thought record
                thought = Thought(content=response_text, tool_calls=tool_calls)

                if not tool_calls:
                    # No tools to execute — we have our final answer
                    thought.tool_results = []
                    self.thoughts.append(thought)
                    final_response = response_text
                    break

                # Execute tools
                self.status = AgentStatus.ACTING
                tool_results = await self._execute_tools(tool_calls)
                thought.tool_results = tool_results
                self.thoughts.append(thought)
                self.actions_taken += len(tool_calls)

                # Add tool results to message context for next round
                messages.append({"role": "assistant", "content": response_text})

                results_text = "\n".join(
                    f"Tool '{r.get('tool', 'unknown')}' result: {r.get('result', r.get('error', 'no output'))}"
                    for r in tool_results
                )
                messages.append({"role": "user", "content": f"Tool results:\n{results_text}"})

            else:
                # Reached max rounds — use last response
                final_response = response_text if response_text else "Max tool rounds reached."

            self.status = AgentStatus.COMPLETED

        except Exception as e:
            self.status = AgentStatus.ERROR
            final_response = f"Error during thinking: {str(e)}"
            logger.error("Agent %s think() error: %s", self.name, e, exc_info=True)

        # Store result in vector memory for future recall
        if final_response and self.status == AgentStatus.COMPLETED:
            try:
                from memory.vector_store import vector_store
                if vector_store.is_available:
                    await vector_store.add_documents(
                        collection_name=f"agent_{self.role.value}",
                        documents=[f"Task: {task[:200]}\nResult: {final_response[:500]}"],
                        metadatas=[{
                            "agent_id": self.id,
                            "role": self.role.value,
                            "timestamp": str(time.time()),
                        }],
                    )
            except Exception as e:
                logger.debug("Vector store save failed (non-fatal): %s", e)

        # Post completion to message bus
        await self._publish_status(final_response)

        self.last_active = time.time()
        return final_response

    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """Call Ollama /api/chat endpoint with circuit breaker protection.

        Args:
            messages: List of message dicts with 'role' and 'content'.

        Returns:
            The assistant's response text.

        Raises:
            httpx.HTTPStatusError: On non-2xx response (after circuit allows).
            httpx.TimeoutException: On timeout (after circuit allows).
            RuntimeError: If circuit breaker is open (Ollama unavailable).
        """
        # Check circuit breaker before attempting call
        try:
            from services.resilience import ollama_breaker
            if not ollama_breaker.is_available:
                raise RuntimeError(
                    f"Ollama circuit breaker is OPEN for agent {self.name}. "
                    f"Service appears down. Will retry after recovery timeout."
                )
        except ImportError:
            pass

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 4096,
            },
        }

        try:
            response = await self.http_client.post("/api/chat", json=payload)
            response.raise_for_status()

            data = response.json()
            content = data.get("message", {}).get("content", "")

            # Record success with circuit breaker
            try:
                from services.resilience import ollama_breaker
                ollama_breaker.record_success()
            except ImportError:
                pass

            # Track token usage if available
            try:
                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)
                if prompt_tokens or completion_tokens:
                    from services.token_tracker import track_usage
                    await track_usage(
                        agent_id=self.id,
                        agent_role=self.role.value,
                        model=self.model,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        playbook_id=self.context.get("playbook_id"),
                    )
            except Exception as tok_err:
                logger.debug("Token tracking failed (non-fatal): %s", tok_err)

            if not content:
                logger.warning("Empty response from LLM for agent %s", self.name)
                return ""

            return content

        except httpx.TimeoutException:
            logger.error("LLM timeout for agent %s (model=%s)", self.name, self.model)
            try:
                from services.resilience import ollama_breaker
                ollama_breaker.record_failure()
            except ImportError:
                pass
            raise
        except httpx.HTTPStatusError as e:
            logger.error(
                "LLM HTTP error for agent %s: %d %s",
                self.name,
                e.response.status_code,
                e.response.text[:200],
            )
            try:
                from services.resilience import ollama_breaker
                ollama_breaker.record_failure()
            except ImportError:
                pass
            raise
        except Exception as e:
            if "circuit breaker" not in str(e).lower():
                try:
                    from services.resilience import ollama_breaker
                    ollama_breaker.record_failure()
                except ImportError:
                    pass
            logger.error("LLM call failed for agent %s: %s", self.name, e)
            raise

    async def _execute_tools(self, tool_calls: List[ToolCall]) -> List[Dict[str, Any]]:
        """Execute parsed tool calls.

        This base implementation returns a placeholder. Subclasses or the
        factory should inject a real tool executor.

        Args:
            tool_calls: List of ToolCall instances to execute.

        Returns:
            List of result dicts with keys: tool, result/error.
        """
        results: List[Dict[str, Any]] = []

        for call in tool_calls:
            try:
                result = await self._run_single_tool(call)
                results.append({
                    "tool": call.name,
                    "arguments": call.arguments,
                    "result": result,
                })
            except Exception as e:
                logger.error(
                    "Tool execution failed: %s(%s) - %s",
                    call.name,
                    call.arguments,
                    e,
                )
                results.append({
                    "tool": call.name,
                    "arguments": call.arguments,
                    "error": str(e),
                })

        return results

    async def _run_single_tool(self, tool_call: ToolCall) -> str:
        """Execute a single tool call.

        Override this method to provide actual tool execution.
        The default implementation raises NotImplementedError for unknown tools.
        """
        # Check if there's a registered tool executor
        if hasattr(self, "_tool_executor") and self._tool_executor is not None:
            return await self._tool_executor(tool_call.name, tool_call.arguments)

        return f"Tool '{tool_call.name}' is not available in this agent's context."

    def set_tool_executor(
        self,
        executor: Any,  # Callable[[str, Dict], Awaitable[str]]
    ) -> None:
        """Inject a tool executor function.

        Args:
            executor: Async callable(name, arguments) -> str result.
        """
        self._tool_executor = executor

    async def _publish_status(self, result: str) -> None:
        """Publish a status update to the message bus."""
        try:
            await self._bus.publish(
                topic=Topic.STATUS_UPDATE,
                payload={
                    "agent_id": self.id,
                    "agent_name": self.name,
                    "role": self.role.value,
                    "status": self.status.value,
                    "result_preview": result[:200] if result else "",
                    "actions_taken": self.actions_taken,
                },
                sender_id=self.id,
            )
        except Exception as e:
            logger.debug("Failed to publish status: %s", e)

    async def retire(self) -> None:
        """Retire this agent, cleaning up resources."""
        self.status = AgentStatus.RETIRED

        # Unsubscribe from all bus topics
        self._bus.unsubscribe_all(self.id)

        # Close HTTP client
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

        # Publish retirement notice
        try:
            await get_message_bus().publish(
                topic=Topic.AGENT_RETIRED,
                payload={
                    "agent_id": self.id,
                    "agent_name": self.name,
                    "role": self.role.value,
                    "actions_taken": self.actions_taken,
                    "lifetime_seconds": time.time() - self.created_at,
                },
                sender_id=self.id,
            )
        except Exception as e:
            logger.debug("Failed to publish retirement notice: %s", e)

        logger.info(
            "Agent retired: %s (actions=%d, lifetime=%.1fs)",
            self.name,
            self.actions_taken,
            time.time() - self.created_at,
        )

    def get_state(self) -> AgentState:
        """Get a serializable snapshot of this agent's state."""
        return AgentState(
            id=self.id,
            role=self.role.value,
            name=self.name,
            status=self.status.value,
            model=self.model,
            actions_taken=self.actions_taken,
            thoughts_count=len(self.thoughts),
            created_at=self.created_at,
            last_active=self.last_active,
        )

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"name={self.name!r} role={self.role.value!r} "
            f"status={self.status.value!r}>"
        )
