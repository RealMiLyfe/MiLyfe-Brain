"""MiLyfe Brain — Pydantic Models & Enums.

All shared data models for the application. Used by API routes,
agents, services, and database serialization.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════


class AgentRole(str, Enum):
    """Roles an agent can assume in the swarm."""

    orchestrator = "orchestrator"
    researcher = "researcher"
    coder = "coder"
    executor = "executor"
    critic = "critic"
    designer = "designer"
    writer = "writer"
    debugger = "debugger"
    planner = "planner"


class TaskStatus(str, Enum):
    """Lifecycle states of a task or playbook step."""

    pending = "pending"
    running = "running"
    awaiting_approval = "awaiting_approval"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskComplexity(str, Enum):
    """Complexity tiers that determine model selection."""

    light = "light"
    medium = "medium"
    heavy = "heavy"


class ActionType(str, Enum):
    """Types of actions agents can perform (subject to permission gates)."""

    file_read = "file_read"
    file_write = "file_write"
    file_delete = "file_delete"
    shell_exec = "shell_exec"
    browse_web = "browse_web"
    gui_action = "gui_action"
    code_exec = "code_exec"
    llm_call = "llm_call"
    memory_store = "memory_store"
    memory_recall = "memory_recall"


# ═══════════════════════════════════════════════════════════════════════
# PLAYBOOK MODELS
# ═══════════════════════════════════════════════════════════════════════


class PlaybookStep(BaseModel):
    """A single step within a playbook execution plan."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    agent_role: Optional[AgentRole] = None
    depends_on: List[str] = Field(default_factory=list)
    complexity: TaskComplexity = TaskComplexity.medium
    tools_needed: List[str] = Field(default_factory=list)


class PlaybookCreate(BaseModel):
    """Request model for creating a new playbook."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="")
    raw_text: Optional[str] = None
    steps: List[PlaybookStep] = Field(default_factory=list)
    auto_execute: bool = False


class Playbook(BaseModel):
    """Full playbook representation with execution state."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.pending
    steps: List[PlaybookStep] = Field(default_factory=list)
    raw_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════
# AGENT MODELS
# ═══════════════════════════════════════════════════════════════════════


class AgentState(BaseModel):
    """Runtime state of an agent in the swarm."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: AgentRole
    name: str
    status: TaskStatus = TaskStatus.pending
    current_task: Optional[str] = None
    thoughts: List[str] = Field(default_factory=list)
    actions_taken: int = 0
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    model: Optional[str] = None
    avatar_color: str = Field(default="#6366f1")


# ═══════════════════════════════════════════════════════════════════════
# STREAMING / EVENTS
# ═══════════════════════════════════════════════════════════════════════


class StreamEvent(BaseModel):
    """Server-Sent Event payload for real-time agent updates."""

    event_type: str
    agent_id: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════
# APPROVAL / SAFETY
# ═══════════════════════════════════════════════════════════════════════


class ApprovalRequest(BaseModel):
    """Request for human approval before a dangerous action."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_type: ActionType
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)
    agent_id: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    risk_level: str = Field(default="medium", pattern=r"^(low|medium|high|critical)$")


# ═══════════════════════════════════════════════════════════════════════
# CHAT MODELS
# ═══════════════════════════════════════════════════════════════════════


class ChatMessage(BaseModel):
    """A single message in a chat session."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    role: str = Field(..., pattern=r"^(user|assistant|system|tool)$")
    content: str
    model: Optional[str] = None
    tokens_used: int = 0
    tool_calls: Optional[List[Dict[str, Any]]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════
# GRAPH VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════


class GraphNode(BaseModel):
    """Node in the agent execution graph (for React Flow)."""

    id: str
    label: str
    type: str = "default"
    status: TaskStatus = TaskStatus.pending
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    data: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Edge in the agent execution graph (for React Flow)."""

    id: str
    source: str
    target: str
    label: Optional[str] = None
    animated: bool = False


# ═══════════════════════════════════════════════════════════════════════
# API REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════


class HealthResponse(BaseModel):
    """Health check endpoint response."""

    status: str = "healthy"
    version: str = ""
    uptime_seconds: float = 0.0
    ollama_connected: bool = False
    chromadb_connected: bool = False
    database_connected: bool = True
    models_available: List[str] = Field(default_factory=list)


class ChatSendRequest(BaseModel):
    """Request body for sending a chat message."""

    message: str = Field(..., min_length=1)
    session_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    model: Optional[str] = None
    context_files: List[str] = Field(default_factory=list)


class NotificationModel(BaseModel):
    """Notification data model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    message: str
    type: str = Field(default="info", pattern=r"^(info|warning|error|success)$")
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class ScheduledJob(BaseModel):
    """Scheduled / cron job model."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    playbook_id: Optional[str] = None
    title: str
    cron_expression: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class TokenUsage(BaseModel):
    """Token usage tracking entry."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    model: str
    playbook_id: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class SettingsUpdate(BaseModel):
    """Request body for updating application settings."""

    key: str = Field(..., min_length=1, max_length=100)
    value: str
