"""MiLyfe Brain — All Pydantic Models / API Schemas."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================


class AgentRole(str, enum.Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    CODER = "coder"
    EXECUTOR = "executor"
    CRITIC = "critic"
    DESIGNER = "designer"
    WRITER = "writer"
    DEBUGGER = "debugger"
    PLANNER = "planner"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskComplexity(str, enum.Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class ActionType(str, enum.Enum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SHELL_EXEC = "shell_exec"
    BROWSE_WEB = "browse_web"
    GUI_ACTION = "gui_action"
    CODE_EXEC = "code_exec"
    LLM_CALL = "llm_call"
    MEMORY_STORE = "memory_store"
    MEMORY_RECALL = "memory_recall"


class PermissionLevel(str, enum.Enum):
    FREE = "free"
    NOTIFY = "notify"
    APPROVE = "approve"
    BLOCKED = "blocked"


class RiskLevel(str, enum.Enum):
    SAFE = "safe"
    CAUTION = "caution"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class EventType(str, enum.Enum):
    AGENT_SPAWNED = "agent_spawned"
    THOUGHT = "thought"
    ACTION = "action"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PROGRESS = "progress"
    ERROR = "error"
    COMPLETED = "completed"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_RESOLVED = "approval_resolved"
    PLAYBOOK_STARTED = "playbook_started"
    PLAYBOOK_COMPLETED = "playbook_completed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"


class TopicType(str, enum.Enum):
    NEW_TASK = "new_task"
    FOLLOW_UP = "follow_up"
    QUESTION = "question"
    EDIT = "edit"
    COMMAND = "command"
    FEEDBACK = "feedback"
    CLARIFICATION = "clarification"


class OutputStyle(str, enum.Enum):
    DEFAULT = "default"
    CONCISE = "concise"
    VERBOSE = "verbose"
    ARCHITECT = "architect"
    PAIR_PROGRAMMER = "pair_programmer"
    DIFF_ONLY = "diff_only"
    JUNIOR_FRIENDLY = "junior_friendly"
    TUTORIAL = "tutorial"


class NotificationType(str, enum.Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    APPROVAL = "approval"


class PlaybookStatus(str, enum.Enum):
    QUEUED = "queued"
    PARSING = "parsing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================
# Core Models
# ============================================================


class PlaybookStep(BaseModel):
    id: str
    description: str
    agent_role: Optional[AgentRole] = None
    depends_on: List[str] = Field(default_factory=list)
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    tools_needed: List[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class PlaybookCreate(BaseModel):
    title: str = Field(..., max_length=500)
    description: str = Field(..., max_length=50000)
    raw_text: Optional[str] = Field(None, max_length=100000)
    steps: Optional[List[PlaybookStep]] = Field(None, max_length=50)
    auto_execute: bool = True
    model_override: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class Playbook(BaseModel):
    id: str
    title: str
    description: str
    raw_text: Optional[str] = None
    steps: List[PlaybookStep] = Field(default_factory=list)
    status: PlaybookStatus = PlaybookStatus.QUEUED
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    model_override: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    total_tokens: int = 0


class AgentState(BaseModel):
    id: str
    role: AgentRole
    name: str
    status: str = "idle"
    current_task: Optional[str] = None
    thoughts: List[str] = Field(default_factory=list)
    actions_taken: int = 0
    progress: float = 0.0
    model: str = ""
    avatar_color: str = "#5c7cfa"
    spawned_at: datetime = Field(default_factory=datetime.utcnow)


class StreamEvent(BaseModel):
    event_type: EventType
    agent_id: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    playbook_id: Optional[str] = None


class ApprovalRequest(BaseModel):
    id: str
    action_type: ActionType
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)
    agent_id: str
    agent_role: AgentRole
    risk_level: RiskLevel
    playbook_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalResponse(BaseModel):
    approved: bool
    reason: Optional[str] = None


# ============================================================
# Graph Visualization
# ============================================================


class GraphPosition(BaseModel):
    x: float
    y: float


class GraphNode(BaseModel):
    id: str
    label: str
    type: str = "step"
    status: TaskStatus = TaskStatus.PENDING
    position: GraphPosition = Field(default_factory=lambda: GraphPosition(x=0, y=0))
    data: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None
    animated: bool = False


class TaskGraph(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


# ============================================================
# Chat
# ============================================================


class ChatMessage(BaseModel):
    id: str
    session_id: str
    role: str  # "user", "assistant", "system", "tool"
    content: str
    model: Optional[str] = None
    tokens_used: int = 0
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    attachments: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatSend(BaseModel):
    message: str = Field(..., max_length=50000)
    session_id: Optional[str] = None
    model_override: Optional[str] = None
    output_style: OutputStyle = OutputStyle.DEFAULT
    attachments: List[str] = Field(default_factory=list)


class ChatSession(BaseModel):
    id: str
    title: str
    message_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Documents
# ============================================================


class DocumentUpload(BaseModel):
    filename: str
    content_type: str
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentSearch(BaseModel):
    query: str = Field(..., max_length=5000)
    limit: int = Field(5, ge=1, le=50)
    collection: Optional[str] = None


class DocumentResult(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    distance: float = 0.0


# ============================================================
# Scheduler
# ============================================================


class ScheduledJob(BaseModel):
    id: str
    playbook_id: Optional[str] = None
    title: str
    cron_expression: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScheduledJobCreate(BaseModel):
    title: str = Field(..., max_length=200)
    playbook_id: Optional[str] = None
    cron_expression: str = Field(..., max_length=100)
    enabled: bool = True


# ============================================================
# Notifications
# ============================================================


class Notification(BaseModel):
    id: str
    title: str
    message: str
    type: NotificationType = NotificationType.INFO
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Token Tracking
# ============================================================


class TokenUsage(BaseModel):
    id: str
    agent_id: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    model: str
    playbook_id: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TokenStats(BaseModel):
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    by_model: Dict[str, int] = Field(default_factory=dict)
    by_role: Dict[str, int] = Field(default_factory=dict)
    cost_equivalent_usd: float = 0.0  # What this would cost on OpenAI


# ============================================================
# Queue
# ============================================================


class QueueItem(BaseModel):
    playbook_id: str
    title: str
    status: PlaybookStatus
    position: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QueueStatus(BaseModel):
    running: Optional[QueueItem] = None
    waiting: List[QueueItem] = Field(default_factory=list)
    completed: List[QueueItem] = Field(default_factory=list)
    total_processed: int = 0


# ============================================================
# Settings
# ============================================================


class RuntimeSettings(BaseModel):
    light_model: str = "phi3:mini"
    heavy_model: str = "llama3.1:8b"
    premium_model: str = "llama3.1:70b"
    require_approval_destructive: bool = True
    require_approval_browsing: bool = True
    require_approval_gui: bool = True
    auto_git_snapshots: bool = True
    output_style: OutputStyle = OutputStyle.DEFAULT
    max_retries: int = 3
    context_summarize_threshold: int = 32000


# ============================================================
# Logs
# ============================================================


class ActionLog(BaseModel):
    id: str
    playbook_id: Optional[str] = None
    agent_id: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    action_type: ActionType
    description: str
    result: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.SAFE
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LogFilter(BaseModel):
    agent_role: Optional[AgentRole] = None
    action_type: Optional[ActionType] = None
    playbook_id: Optional[str] = None
    risk_level: Optional[RiskLevel] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(50, ge=1, le=500)
    offset: int = Field(0, ge=0)


# ============================================================
# Workspace
# ============================================================


class FileNode(BaseModel):
    name: str
    path: str
    is_dir: bool = False
    size: int = 0
    modified: Optional[datetime] = None
    children: List["FileNode"] = Field(default_factory=list)


class WorkspaceTree(BaseModel):
    root: str
    tree: List[FileNode] = Field(default_factory=list)
    total_files: int = 0
    total_dirs: int = 0


# ============================================================
# Self-Test
# ============================================================


class SelfTestResult(BaseModel):
    service: str
    status: str  # "pass", "fail", "skip"
    message: str
    latency_ms: float = 0.0


class SelfTestReport(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    results: List[SelfTestResult] = Field(default_factory=list)
    all_passed: bool = False
    total_latency_ms: float = 0.0


# ============================================================
# Export/Import
# ============================================================


class PlaybookExport(BaseModel):
    version: str = "1.0"
    exported_at: datetime = Field(default_factory=datetime.utcnow)
    playbook: Playbook
    steps: List[PlaybookStep] = Field(default_factory=list)


# ============================================================
# Skills
# ============================================================


class Skill(BaseModel):
    id: str
    name: str
    description: str
    category: str
    steps_json: str
    source_playbook_id: Optional[str] = None
    success_count: int = 0
    triggers: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Memory
# ============================================================


class AgentMemory(BaseModel):
    id: str
    role: AgentRole
    memory_type: str  # "fact", "procedure", "episode", "semantic"
    content: str
    importance: float = 0.5
    recall_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Daemon
# ============================================================


class DaemonStatus(BaseModel):
    running: bool = False
    watching_paths: List[str] = Field(default_factory=list)
    events_processed: int = 0
    last_event: Optional[datetime] = None


# ============================================================
# Health
# ============================================================


class HealthStatus(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"
    services: Dict[str, str] = Field(default_factory=dict)
    uptime_seconds: float = 0.0


# ============================================================
# Tool System
# ============================================================


class ToolDefinition(BaseModel):
    name: str
    category: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    permission: PermissionLevel = PermissionLevel.FREE
    returns: str = "string"


class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    call_id: Optional[str] = None


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    output: str = ""
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    call_id: Optional[str] = None


# ============================================================
# Scratchpad
# ============================================================


class ScratchpadEntry(BaseModel):
    id: str
    category: str  # "todo", "note", "decision", "finding", "blocker"
    content: str
    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# MCP (Model Context Protocol)
# ============================================================


class MCPToolSchema(BaseModel):
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)


class MCPToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = None


class MCPToolResult(BaseModel):
    request_id: Optional[str] = None
    success: bool
    output: Any = None
    error: Optional[str] = None


# Enable self-referencing models
FileNode.model_rebuild()
