"""
MiLyfe Brain - API Layer

Tag metadata for OpenAPI documentation and route organization.
"""
from __future__ import annotations

TAGS_METADATA = [
    {
        "name": "playbooks",
        "description": "Create, manage, and execute playbooks (multi-step agent workflows).",
    },
    {
        "name": "agents",
        "description": "Monitor and manage the AI agent swarm.",
    },
    {
        "name": "chat",
        "description": "Hybrid chat interface with session management.",
    },
    {
        "name": "tasks",
        "description": "Task and step management within playbooks.",
    },
    {
        "name": "streaming",
        "description": "Real-time event streaming via SSE and WebSocket.",
    },
    {
        "name": "health",
        "description": "System health checks and diagnostics.",
    },
    {
        "name": "settings",
        "description": "Runtime configuration and model settings.",
    },
    {
        "name": "documents",
        "description": "Document upload, indexing, and semantic search via ChromaDB.",
    },
    {
        "name": "selftest",
        "description": "Self-test and connectivity verification.",
    },
    {
        "name": "workspace",
        "description": "Workspace management and git integration.",
    },
    {
        "name": "download",
        "description": "File download and export endpoints.",
    },
    {
        "name": "notifications",
        "description": "User notification management.",
    },
    {
        "name": "logs",
        "description": "Action audit logs and filtering.",
    },
    {
        "name": "scheduler",
        "description": "Scheduled job management (cron-like).",
    },
    {
        "name": "tokens",
        "description": "Token usage tracking and statistics.",
    },
    {
        "name": "queue",
        "description": "Playbook execution queue management.",
    },
    {
        "name": "filesystem",
        "description": "File system browsing and operations.",
    },
    {
        "name": "daemon",
        "description": "Background daemon status and control.",
    },
    {
        "name": "export_import",
        "description": "Playbook export and import for sharing.",
    },
    {
        "name": "brain",
        "description": "Core brain orchestration and introspection.",
    },
]
