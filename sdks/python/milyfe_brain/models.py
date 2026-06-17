"""Data models for the MiLyfe Brain SDK."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    ORCHESTRATOR = "orchestrator"
    RESEARCHER = "researcher"
    CODER = "coder"
    EXECUTOR = "executor"
    CRITIC = "critic"
    DESIGNER = "designer"
    WRITER = "writer"
    DEBUGGER = "debugger"
    PLANNER = "planner"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskComplexity(str, Enum):
    LIGHT = "light"
    MEDIUM = "medium"
    HEAVY = "heavy"


class PlaybookStep(BaseModel):
    id: str
    description: str
    agent_role: Optional[AgentRole] = None
    depends_on: List[str] = Field(default_factory=list)
    complexity: TaskComplexity = TaskComplexity.MEDIUM
    tools_needed: List[str] = Field(default_factory=list)
    status: Optional[TaskStatus] = None
    result: Optional[str] = None


class PlaybookCreate(BaseModel):
    title: str
    description: str
    raw_text: Optional[str] = None
    steps: Optional[List[PlaybookStep]] = None
    auto_execute: bool = True


class Playbook(BaseModel):
    id: str
    title: str
    description: str
    status: TaskStatus
    steps: List[PlaybookStep] = Field(default_factory=list)
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class AgentState(BaseModel):
    id: str
    role: AgentRole
    name: str
    status: str
    current_task: Optional[str] = None
    thoughts: List[str] = Field(default_factory=list)
    actions_taken: int = 0
    progress: float = 0.0
    model: str = ""
    avatar_color: str = ""


class StreamEvent(BaseModel):
    event_type: str
    agent_id: Optional[str] = None
    agent_role: Optional[AgentRole] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime


class ChatMessage(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    model: Optional[str] = None
    tokens_used: int = 0
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class ApprovalRequest(BaseModel):
    id: str
    action_type: str
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)
    agent_id: str
    agent_role: AgentRole
    risk_level: str


class HealthResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]
    uptime_seconds: float


class TokenStats(BaseModel):
    total_prompt_tokens: int
    total_completion_tokens: int
    by_model: Dict[str, int]
    by_role: Dict[str, int]
