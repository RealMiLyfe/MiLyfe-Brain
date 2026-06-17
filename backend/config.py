"""
MiLyfe Brain - Configuration Settings

Central configuration using Pydantic Settings with environment variable support.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- External Services ---
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama API base URL")
    chroma_url: str = Field(default="http://localhost:8400", description="ChromaDB REST API URL")
    redis_url: str = Field(default="redis://localhost:6479", description="Redis connection URL")
    database_url: str = Field(default="sqlite+aiosqlite:///./data/milyfe_brain.db", description="SQLAlchemy database URL")

    # --- Model Configuration ---
    default_light_model: str = Field(default="phi3:mini", description="Fast model for simple tasks")
    default_heavy_model: str = Field(default="hermes3:latest", description="Heavy model for complex reasoning")
    premium_model: str = Field(default="qwen2.5:14b", description="Premium model for highest quality")

    # --- Agent Limits ---
    max_agents: int = Field(default=10, description="Maximum concurrent agents")
    agent_timeout: int = Field(default=300, description="Agent execution timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts for failed operations")
    max_tool_rounds: int = Field(default=3, description="Maximum tool call rounds per agent turn")
    max_batch_parallel: int = Field(default=10, description="Maximum parallel batch operations")

    # --- Safety & Approvals ---
    require_approval_destructive: bool = Field(default=True, description="Require approval for destructive operations")
    require_approval_browsing: bool = Field(default=True, description="Require approval for browser automation")
    require_approval_gui: bool = Field(default=True, description="Require approval for GUI automation")

    # --- Workspace ---
    workspace_dir: str = Field(default="./workspace", description="Working directory for agent operations")
    auto_git_snapshots: bool = Field(default=True, description="Automatically create git snapshots before changes")

    # --- Context Management ---
    context_summarize_threshold: int = Field(default=32000, description="Token threshold to trigger context summarization")

    # --- Authentication ---
    auth_enabled: bool = Field(default=False, description="Enable API key authentication")
    api_key: Optional[str] = Field(default=None, description="API key for authentication (if enabled)")
    cors_allow_all: bool = Field(default=True, description="Allow all CORS origins")

    # --- Server ---
    backend_port: int = Field(default=8200, description="Backend server port")
    rate_limit_per_minute: int = Field(default=120, description="Rate limit requests per minute per IP")
    max_request_size_mb: int = Field(default=10, description="Maximum request body size in megabytes")

    @property
    def workspace_path(self) -> Path:
        """Resolved workspace directory path."""
        return Path(self.workspace_dir).resolve()

    @property
    def data_dir(self) -> Path:
        """Data directory for persistent storage."""
        return Path("./data").resolve()

    @property
    def rules_dirs(self) -> List[Path]:
        """List of directories to search for rule files."""
        return [
            self.workspace_path / ".milyfe" / "rules",
            Path("./rules").resolve(),
        ]

    @property
    def skills_dirs(self) -> List[Path]:
        """List of directories to search for skill files."""
        return [
            self.workspace_path / ".milyfe" / "skills",
            Path("./skills").resolve(),
        ]

    @property
    def config_dirs(self) -> List[Path]:
        """List of directories to search for configuration files."""
        return [
            self.workspace_path / ".milyfe" / "config",
            Path("./config").resolve(),
        ]


settings = Settings()
