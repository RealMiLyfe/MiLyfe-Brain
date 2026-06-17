"""MiLyfe Brain — API Module with OpenAPI Tag Metadata."""

TAGS_METADATA = [
    {"name": "playbooks", "description": "Playbook CRUD and execution"},
    {"name": "agents", "description": "Agent spawning, tracking, and retirement"},
    {"name": "chat", "description": "Hybrid chat with tool execution"},
    {"name": "tasks", "description": "Task management"},
    {"name": "streaming", "description": "WebSocket and SSE real-time events"},
    {"name": "health", "description": "Health check endpoint"},
    {"name": "settings", "description": "Runtime settings management"},
    {"name": "documents", "description": "Document upload and semantic search"},
    {"name": "selftest", "description": "End-to-end self-test"},
    {"name": "workspace", "description": "Workspace file management"},
    {"name": "download", "description": "Download workspace as zip"},
    {"name": "notifications", "description": "Notification center"},
    {"name": "logs", "description": "Action log search and export"},
    {"name": "scheduler", "description": "Scheduled job management"},
    {"name": "tokens", "description": "Token usage statistics"},
    {"name": "queue", "description": "Playbook execution queue"},
    {"name": "filesystem", "description": "Local filesystem browser"},
    {"name": "daemon", "description": "Autonomous daemon control"},
    {"name": "export_import", "description": "Playbook backup and restore"},
]
