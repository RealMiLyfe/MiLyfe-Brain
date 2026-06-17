"""
MiLyfe Brain - Pydantic Models & Schemas

All API request/response models, enums, and data structures.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# ============================================================
# Enums
# ============================================================


class AgentRole(str, Enum):
    """Specialized agent roles in the swarm."""
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    EXECUTOR = "executor"
    REVIEWER = "reviewer"
    WRITER = "writer"
    BROWSER = "browser"
    GUI = "gui"
    ORCHESTRATOR = "orchestrator"


class TaskStatus(str, Enum):
    """Status of a task or playbook step."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class TaskComplexity(str, Enum):
    """Complexity level of a task."""
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class ActionType(str, Enum):
    """Types of actions that can be performed."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    SHELL_EXEC = "shell_exec"
    BROWSER_NAV = "browser_nav"
    GUI_ACTION = "gui_action"
    SEARCH = "search"
    CODE_EXEC = "code_exec"
    API_CALL = "api_call"
    MEMORY_STORE = "memory_store"
    MEMORY_RECALL = "memory_recall"


class PermissionLevel(str, Enum):
    """Permission levels for operations."""
    SAFE = "safe"
    MODERATE = "moderate"
    DESTRUCTIVE = "destructive"
    CRITICAL = "critical"


class RiskLevel(str, Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Types of streaming events."""
    PLAYBOOK_STARTED = "playbook_started"
    PLAYBOOK_COMPLETED = "playbook_completed"
    PLAYBOOK_FAILED = "playbook_failed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    AGENT_THINKING = "agent_thinking"
    AGENT_ACTING = "agent_acting"
    AGENT_TOOL_CALL = "agent_tool_call"
    AGENT_TOOL_RESULT = "agent_tool_result"
    AGENT_MESSAGE = "agent_message"
    APPROVAL_NEEDED = "approval_needed"
    APPROVAL_RESOLVED = "approval_resolved"
    TOKEN_USAGE = "token_usage"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    QUEUE_UPDATE = "queue_update"
    NOTIFICATION = "notification"


class TopicType(str, Enum):
    """Topic types for conversation classification."""
    GENERAL = "general"
    CODING = "coding"
    RESEARCH = "research"
    WRITING = "writing"
    PLANNING = "planning"
    DEBUGGING = "debugging"
    BRAINSTORMING = "brainstorming"
    ANALYSIS = "analysis"


class OutputStyle(str, Enum):
    """Output formatting styles."""
    CONCISE = "concise"
    DETAILED = "detailed"
    MARKDOWN = "markdown"
    CODE_ONLY = "code_only"
    STEP_BY_STEP = "step_by_step"
    BULLET_POINTS = "bullet_points"
    CONVERSATIONAL = "conversational"
    TECHNICAL = "technical"


class NotificationType(str, Enum):
    """Types of user notifications."""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    APPROVAL = "approval"


class PlaybookStatus(str, Enum):
    """Status of a playbook."""
    DRAFT = "draft"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================
# Playbook Models
# ============================================================


class PlaybookStep(BaseModel):
    """A single step within a playbook."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(..., description="Step title")
    description: str = Field(default="", description="Step description")
    agent_role: AgentRole = Field(default=AgentRole.ORCHESTRATOR, description="Assigned agent role")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    order: int = Field(default=0, description="Execution order")
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite steps")
    output: Optional[str] = Field(default=None, description="Step output/result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    retries: int = Field(default=0)


class PlaybookCreate(BaseModel):
    """Request to create a new playbook."""
    title: str = Field(..., description="Playbook title")
    goal: str = Field(..., description="Natural language goal description")
    context: Optional[str] = Field(default=None, description="Additional context")
    priority: int = Field(default=5, ge=1, le=10, description="Priority 1-10")
    tags: List[str] = Field(default_factory=list)


class Playbook(BaseModel):
    """Complete playbook with steps."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    goal: str
    context: Optional[str] = Field(default=None)
    status: PlaybookStatus = Field(default=PlaybookStatus.DRAFT)
    priority: int = Field(default=5)
    tags: List[str] = Field(default_factory=list)
    steps: List[PlaybookStep] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    total_tokens: int = Field(default=0)
    error: Optional[str] = Field(default=None)


# ============================================================
# Agent Models
# ============================================================


class AgentState(BaseModel):
    """Current state of an agent."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: AgentRole
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    current_task: Optional[str] = Field(default=None)
    playbook_id: Optional[str] = Field(default=None)
    step_id: Optional[str] = Field(default=None)
    thinking: Optional[str] = Field(default=None)
    last_action: Optional[str] = Field(default=None)
    tokens_used: int = Field(default=0)
    started_at: Optional[datetime] = Field(default=None)
    model: Optional[str] = Field(default=None)


# ============================================================
# Streaming Models
# ============================================================


class StreamEvent(BaseModel):
    """A server-sent event for real-time updates."""
    event_type: EventType
    playbook_id: Optional[str] = Field(default=None)
    step_id: Optional[str] = Field(default=None)
    agent_role: Optional[AgentRole] = Field(default=None)
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Approval Models
# ============================================================


class ApprovalRequest(BaseModel):
    """Request for user approval of a risky action."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    playbook_id: str
    step_id: str
    agent_role: AgentRole
    action_type: ActionType
    risk_level: RiskLevel
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)


class ApprovalResponse(BaseModel):
    """User response to an approval request."""
    approved: bool
    reason: Optional[str] = Field(default=None)
    remember: bool = Field(default=False, description="Remember this decision for similar actions")


# ============================================================
# Task Graph Models
# ============================================================


class GraphPosition(BaseModel):
    """Position coordinates for graph visualization."""
    x: float = Field(default=0.0)
    y: float = Field(default=0.0)


class GraphNode(BaseModel):
    """A node in the task execution graph."""
    id: str
    label: str
    role: Optional[AgentRole] = Field(default=None)
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    position: GraphPosition = Field(default_factory=GraphPosition)


class GraphEdge(BaseModel):
    """An edge connecting two nodes in the task graph."""
    source: str
    target: str
    label: Optional[str] = Field(default=None)


class TaskGraph(BaseModel):
    """Complete task execution graph for visualization."""
    playbook_id: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


# ============================================================
# Chat Models
# ============================================================


class ChatMessage(BaseModel):
    """A single chat message."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    role: str = Field(..., description="Message role: user, assistant, system")
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatSend(BaseModel):
    """Request to send a chat message."""
    session_id: Optional[str] = Field(default=None, description="Session ID (auto-created if None)")
    content: str = Field(..., description="Message content")
    output_style: OutputStyle = Field(default=OutputStyle.CONVERSATIONAL)
    model: Optional[str] = Field(default=None, description="Override model for this message")


class ChatSession(BaseModel):
    """A chat session."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: Optional[str] = Field(default=None)
    topic: TopicType = Field(default=TopicType.GENERAL)
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    message_count: int = Field(default=0)


# ============================================================
# Document Models
# ============================================================


class DocumentUpload(BaseModel):
    """Request to upload and index a document."""
    filename: str
    content_type: str
    collection: str = Field(default="default", description="ChromaDB collection name")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentSearch(BaseModel):
    """Request to search documents."""
    query: str
    collection: str = Field(default="default")
    n_results: int = Field(default=5, ge=1, le=50)
    filters: Dict[str, Any] = Field(default_factory=dict)


class DocumentResult(BaseModel):
    """A document search result."""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: Optional[str] = Field(default=None)


# ============================================================
# Scheduler Models
# ============================================================


class ScheduledJob(BaseModel):
    """A scheduled job."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    cron_expression: str
    playbook_id: Optional[str] = Field(default=None)
    action: str = Field(default="", description="Action to execute")
    enabled: bool = Field(default=True)
    last_run: Optional[datetime] = Field(default=None)
    next_run: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScheduledJobCreate(BaseModel):
    """Request to create a scheduled job."""
    name: str
    cron_expression: str
    playbook_id: Optional[str] = Field(default=None)
    action: str = Field(default="")
    enabled: bool = Field(default=True)


# ============================================================
# Notification Models
# ============================================================


class Notification(BaseModel):
    """A user notification."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: NotificationType = Field(default=NotificationType.INFO)
    title: str
    message: str
    read: bool = Field(default=False)
    playbook_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Token Tracking Models
# ============================================================


class TokenUsage(BaseModel):
    """Token usage for a single LLM call."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    model: str
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    playbook_id: Optional[str] = Field(default=None)
    agent_role: Optional[AgentRole] = Field(default=None)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TokenStats(BaseModel):
    """Aggregated token statistics."""
    total_prompt_tokens: int = Field(default=0)
    total_completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    by_model: Dict[str, int] = Field(default_factory=dict)
    by_role: Dict[str, int] = Field(default_factory=dict)
    period_start: Optional[datetime] = Field(default=None)
    period_end: Optional[datetime] = Field(default=None)


# ============================================================
# Queue Models
# ============================================================


class QueueItem(BaseModel):
    """An item in the execution queue."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    playbook_id: str
    priority: int = Field(default=5)
    status: TaskStatus = Field(default=TaskStatus.QUEUED)
    position: int = Field(default=0)
    added_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)


class QueueStatus(BaseModel):
    """Current queue status."""
    items: List[QueueItem] = Field(default_factory=list)
    running_count: int = Field(default=0)
    queued_count: int = Field(default=0)
    max_concurrent: int = Field(default=1)


# ============================================================
# Settings Models
# ============================================================


class RuntimeSettings(BaseModel):
    """Runtime-adjustable settings."""
    default_light_model: Optional[str] = Field(default=None)
    default_heavy_model: Optional[str] = Field(default=None)
    premium_model: Optional[str] = Field(default=None)
    max_agents: Optional[int] = Field(default=None)
    agent_timeout: Optional[int] = Field(default=None)
    require_approval_destructive: Optional[bool] = Field(default=None)
    require_approval_browsing: Optional[bool] = Field(default=None)
    require_approval_gui: Optional[bool] = Field(default=None)
    auto_git_snapshots: Optional[bool] = Field(default=None)
    context_summarize_threshold: Optional[int] = Field(default=None)


# ============================================================
# Log Models
# ============================================================


class ActionLog(BaseModel):
    """A logged action."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    playbook_id: Optional[str] = Field(default=None)
    step_id: Optional[str] = Field(default=None)
    agent_role: Optional[AgentRole] = Field(default=None)
    action_type: ActionType
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = Field(default=RiskLevel.LOW)
    success: bool = Field(default=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class LogFilter(BaseModel):
    """Filter criteria for log queries."""
    playbook_id: Optional[str] = Field(default=None)
    agent_role: Optional[AgentRole] = Field(default=None)
    action_type: Optional[ActionType] = Field(default=None)
    risk_level: Optional[RiskLevel] = Field(default=None)
    success: Optional[bool] = Field(default=None)
    since: Optional[datetime] = Field(default=None)
    until: Optional[datetime] = Field(default=None)
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# ============================================================
# Workspace / Filesystem Models
# ============================================================


class FileNode(BaseModel):
    """A file or directory node (self-referencing tree)."""
    name: str
    path: str
    is_dir: bool = Field(default=False)
    size: Optional[int] = Field(default=None)
    modified: Optional[datetime] = Field(default=None)
    children: Optional[List[FileNode]] = Field(default=None)


class WorkspaceTree(BaseModel):
    """Workspace directory tree."""
    root: str
    tree: List[FileNode] = Field(default_factory=list)
    total_files: int = Field(default=0)
    total_dirs: int = Field(default=0)


# ============================================================
# Self-Test Models
# ============================================================


class SelfTestResult(BaseModel):
    """Result of a single self-test."""
    name: str
    passed: bool
    message: str = Field(default="")
    duration_ms: float = Field(default=0.0)


class SelfTestReport(BaseModel):
    """Complete self-test report."""
    passed: bool
    total: int = Field(default=0)
    passed_count: int = Field(default=0)
    failed_count: int = Field(default=0)
    results: List[SelfTestResult] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Export/Import Models
# ============================================================


class PlaybookExport(BaseModel):
    """Exported playbook data for sharing."""
    version: str = Field(default="1.0")
    playbook: Playbook
    metadata: Dict[str, Any] = Field(default_factory=dict)
    exported_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Skill Models
# ============================================================


class Skill(BaseModel):
    """A reusable skill definition."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = Field(default="")
    trigger: Optional[str] = Field(default=None, description="Trigger pattern or command")
    steps: List[str] = Field(default_factory=list)
    agent_role: Optional[AgentRole] = Field(default=None)
    tags: List[str] = Field(default_factory=list)
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================
# Memory Models
# ============================================================


class AgentMemory(BaseModel):
    """An agent memory entry."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    agent_role: AgentRole
    content: str
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    playbook_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(default=None)


# ============================================================
# Daemon & Health Models
# ============================================================


class DaemonStatus(BaseModel):
    """Status of the background daemon."""
    running: bool = Field(default=False)
    uptime_seconds: float = Field(default=0.0)
    active_playbooks: int = Field(default=0)
    queued_playbooks: int = Field(default=0)
    last_heartbeat: Optional[datetime] = Field(default=None)


class HealthStatus(BaseModel):
    """System health status."""
    status: str = Field(default="healthy")
    version: str = Field(default="0.1.0")
    uptime_seconds: float = Field(default=0.0)
    ollama_connected: bool = Field(default=False)
    chroma_connected: bool = Field(default=False)
    redis_connected: bool = Field(default=False)
    database_connected: bool = Field(default=True)
    active_agents: int = Field(default=0)
    queued_playbooks: int = Field(default=0)


# ============================================================
# Tool Models
# ============================================================


class ToolDefinition(BaseModel):
    """Definition of an available tool."""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    permission_level: PermissionLevel = Field(default=PermissionLevel.SAFE)
    agent_roles: List[AgentRole] = Field(default_factory=list, description="Roles allowed to use this tool")


class ToolCall(BaseModel):
    """A tool invocation by an agent."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    agent_role: Optional[AgentRole] = Field(default=None)
    playbook_id: Optional[str] = Field(default=None)
    step_id: Optional[str] = Field(default=None)


class ToolResult(BaseModel):
    """Result of a tool invocation."""
    tool_call_id: str
    success: bool
    output: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
    duration_ms: float = Field(default=0.0)


# ============================================================
# Scratchpad Models
# ============================================================


class ScratchpadEntry(BaseModel):
    """An entry in the agent scratchpad."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    agent_role: AgentRole
    key: str
    value: Any = Field(default=None)
    playbook_id: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


# ============================================================
# MCP (Model Context Protocol) Models
# ============================================================


class MCPToolSchema(BaseModel):
    """Schema for an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    server_name: Optional[str] = Field(default=None)


class MCPToolCall(BaseModel):
    """An MCP tool invocation."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    server_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    timeout: Optional[int] = Field(default=None)


class MCPToolResult(BaseModel):
    """Result from an MCP tool invocation."""
    tool_call_id: str
    success: bool
    content: Optional[Any] = Field(default=None)
    error: Optional[str] = Field(default=None)
    duration_ms: float = Field(default=0.0)


# ============================================================
# Rebuild self-referencing models
# ============================================================

FileNode.model_rebuild()
