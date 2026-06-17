"""MiLyfe Brain Agent System.

Provides the multi-agent swarm infrastructure:
- BaseAgent: Abstract base with think/act loop via Ollama httpx
- AgentFactory: Spawn, track, and manage agent instances
- AgentRole: Enum of available agent roles
- Specialized agents: Orchestrator, Researcher, Coder, Executor,
  Critic, Designer, Writer, Debugger, Planner

Usage:
    from agents import AgentFactory, AgentRole, BaseAgent
    from agents.factory import get_agent_factory

    factory = get_agent_factory()
    agent = factory.spawn(role="coder", model="llama3.1:8b")
    result = await agent.think("Write a Python function to...")
"""

from agents.base import AgentRole, AgentState, AgentStatus, BaseAgent
from agents.factory import AgentFactory, get_agent_factory, reset_agent_factory
from agents.message_bus import (
    Message,
    MessageBus,
    Topic,
    get_message_bus,
    reset_message_bus,
)
from agents.roles import (
    CoderAgent,
    CriticAgent,
    DebuggerAgent,
    DesignerAgent,
    ExecutorAgent,
    OrchestratorAgent,
    PlannerAgent,
    ResearcherAgent,
    WriterAgent,
)
from agents.tool_parser import ToolCall, parse_tool_calls

__all__ = [
    # Core
    "BaseAgent",
    "AgentFactory",
    "AgentRole",
    "AgentState",
    "AgentStatus",
    # Factory
    "get_agent_factory",
    "reset_agent_factory",
    # Message Bus
    "Message",
    "MessageBus",
    "Topic",
    "get_message_bus",
    "reset_message_bus",
    # Role Agents
    "OrchestratorAgent",
    "ResearcherAgent",
    "CoderAgent",
    "ExecutorAgent",
    "CriticAgent",
    "DesignerAgent",
    "WriterAgent",
    "DebuggerAgent",
    "PlannerAgent",
    # Tool Parsing
    "ToolCall",
    "parse_tool_calls",
]
