"""Pydantic Models — All API types and data schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────


class AgentRole(str, Enum):
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
    pending = "pending"
    running = "running"
    awaiting_approval = "awaiting_approval"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskComplexity(str, Enum):
    light = "light"
    medium = "medium"
    heavy = "heavy"


class ActionType(str, Enum):
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


class RiskLevel(str, Enum):
    safe = "safe"
    caution = "caution"
    dangerous = "dangerous"
    blocked = "blocked"


class PermissionLevel(str, Enum):
    free = "free"
    notify = "notify"
    approve = "approve"
    blocked = "blocked"


class NotificationType(str, Enum):
    info = "info"
    success = "success"
    warning = "warning"
    error = "error"


# ─── Playbook Models ─────────────────────────────────────────────────────────


class PlaybookStep(BaseModel):
    id: str = ""
    description: str
    agent_role: Optional[AgentRole] = None
    depends_on: list[str] = Field(default_factory=list)
    complexity: TaskComplexity = TaskComplexity.medium
    tools_needed: list[str] = Field(default_factory=list)


class PlaybookCreate(BaseModel):
    title: str = Field(max_length=500)
    description: str = Field(max_length=50000)
    raw_text: Optional[str] = Field(default=None, max_length=100000)
    steps: Optional[list[PlaybookStep]] = Field(default=None, max_length=50)
    auto_execute: bool = True


class PlaybookResponse(BaseModel):
    id: str
    title: str
    description: str
    raw_text: Optional[str] = None
    status: TaskStatus = TaskStatus.pending
    steps: list[dict] = Field(default_factory=list)
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class PlaybookStatusResponse(BaseModel):
    id: str
    status: TaskStatus
    progress: float = 0.0
    current_step: Optional[str] = None
    steps: list[dict] = Field(default_factory=list)
    error: Optional[str] = None


# ─── Agent Models ─────────────────────────────────────────────────────────────


class AgentState(BaseModel):
    id: str
    role: AgentRole
    name: str
    status: str = "idle"
    current_task: Optional[str] = None
    thoughts: list[str] = Field(default_factory=list)
    actions_taken: list[dict] = Field(default_factory=list)
    progress: float = 0.0
    model: str = ""
    avatar_color: str = "#6b7280"


class AgentSpawnRequest(BaseModel):
    role: AgentRole
    model: Optional[str] = None


class AgentMessageRequest(BaseModel):
    message: str
    context: Optional[str] = None


# ─── Chat Models ──────────────────────────────────────────────────────────────


class ChatMessage(BaseModel):
    role: str
    content: str
    model: Optional[str] = None
    tokens_used: int = 0
    tool_calls: list[dict] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    created_at: Optional[str] = None


class ChatSendRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None
    tools_enabled: bool = True


class ChatResponse(BaseModel):
    response: str
    session_id: str
    tool_calls: list[dict] = Field(default_factory=list)
    model: str = ""
    tokens_used: int = 0


class ChatSession(BaseModel):
    id: str
    title: str
    message_count: int = 0
    created_at: str
    updated_at: str


# ─── Streaming Models ─────────────────────────────────────────────────────────


class StreamEvent(BaseModel):
    event_type: str
    agent_id: Optional[str] = None
    agent_role: Optional[str] = None
    data: dict = Field(default_factory=dict)
    timestamp: str = ""


# ─── Approval Models ─────────────────────────────────────────────────────────


class ApprovalRequest(BaseModel):
    id: str
    action_type: ActionType
    description: str
    details: dict = Field(default_factory=dict)
    agent_id: str
    agent_role: AgentRole
    risk_level: RiskLevel = RiskLevel.caution


class ApprovalResponse(BaseModel):
    approved: bool
    reason: Optional[str] = None


# ─── Graph Models ─────────────────────────────────────────────────────────────


class GraphNode(BaseModel):
    id: str
    label: str
    type: str = "default"
    status: TaskStatus = TaskStatus.pending
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0})
    data: dict = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None
    animated: bool = False


class TaskGraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# ─── Document Models ──────────────────────────────────────────────────────────


class DocumentResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    chunk_count: int = 0
    created_at: str


class DocumentSearchRequest(BaseModel):
    query: str
    limit: int = 5


class DocumentSearchResult(BaseModel):
    id: str
    content: str
    metadata: dict = Field(default_factory=dict)
    score: float = 0.0


# ─── Settings Models ──────────────────────────────────────────────────────────


class SettingsUpdate(BaseModel):
    settings: dict[str, Any]


class SettingsResponse(BaseModel):
    settings: dict[str, Any]


# ─── Scheduler Models ─────────────────────────────────────────────────────────


class ScheduledJobCreate(BaseModel):
    playbook_id: Optional[str] = None
    title: str
    cron_expression: str
    enabled: bool = True


class ScheduledJobResponse(BaseModel):
    id: str
    playbook_id: Optional[str] = None
    title: str
    cron_expression: str
    enabled: bool = True
    last_run: Optional[str] = None
    next_run: Optional[str] = None


# ─── Notification Models ──────────────────────────────────────────────────────


class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    type: NotificationType = NotificationType.info
    read: bool = False
    created_at: str


# ─── Token Models ─────────────────────────────────────────────────────────────


class TokenStats(BaseModel):
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    by_model: dict[str, dict] = Field(default_factory=dict)
    by_role: dict[str, dict] = Field(default_factory=dict)


# ─── Queue Models ─────────────────────────────────────────────────────────────


class QueueStatus(BaseModel):
    running: Optional[dict] = None
    waiting: list[dict] = Field(default_factory=list)
    completed: list[dict] = Field(default_factory=list)
    total_processed: int = 0


# ─── Log Models ───────────────────────────────────────────────────────────────


class ActionLog(BaseModel):
    id: str
    playbook_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_role: Optional[str] = None
    action_type: str
    description: str
    result: Optional[str] = None
    timestamp: str


# ─── Self-Test Models ─────────────────────────────────────────────────────────


class SelfTestResult(BaseModel):
    test_name: str
    passed: bool
    message: str
    duration_ms: float = 0.0


class SelfTestResponse(BaseModel):
    overall: bool
    tests: list[SelfTestResult] = Field(default_factory=list)
    duration_ms: float = 0.0


# ─── Export/Import Models ─────────────────────────────────────────────────────


class PlaybookExport(BaseModel):
    version: str = "1.0"
    playbook: dict
    steps: list[dict] = Field(default_factory=list)
    exported_at: str


# ─── Daemon/Brain Models ─────────────────────────────────────────────────────


class DaemonStatus(BaseModel):
    running: bool = False
    watching: list[str] = Field(default_factory=list)
    processed_count: int = 0
    last_activity: Optional[str] = None


class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    category: str
    success_count: int = 0
    created_at: str


class MemoryResponse(BaseModel):
    id: str
    role: str
    memory_type: str
    content: str
    importance: float = 0.5
    recall_count: int = 0
    created_at: str


class DigestResponse(BaseModel):
    date: str
    summary: str
    highlights: list[str] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)
