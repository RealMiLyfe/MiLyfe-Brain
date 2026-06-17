"""MiLyfe Brain — Application Configuration (Pydantic Settings)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Service URLs ---
    ollama_base_url: str = "http://host.docker.internal:11434"
    chroma_url: str = "http://chromadb:8000"
    redis_url: str = "redis://redis:6379/0"

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:////data/milyfe.db"

    # --- Models ---
    default_light_model: str = "phi3:mini"
    default_heavy_model: str = "llama3.1:8b"
    premium_model: str = "llama3.1:70b"

    # --- Agent Config ---
    max_agents: int = 10
    agent_timeout: int = 300
    max_retries: int = 3
    max_tool_rounds: int = 3
    max_batch_parallel: int = 10

    # --- Safety / Approvals ---
    require_approval_destructive: bool = True
    require_approval_browsing: bool = True
    require_approval_gui: bool = True

    # --- Workspace ---
    workspace_dir: str = "/workspace"
    auto_git_snapshots: bool = True

    # --- Context ---
    context_summarize_threshold: int = 32000

    # --- Auth ---
    auth_enabled: bool = False
    api_key: str = "change-me-to-a-real-secret"
    cors_allow_all: bool = True

    # --- Server ---
    backend_port: int = 8200

    # --- Rate Limiting ---
    rate_limit_per_minute: int = 120
    max_request_size_mb: int = 10

    # --- Paths ---
    @property
    def workspace_path(self) -> Path:
        return Path(self.workspace_dir)

    @property
    def data_dir(self) -> Path:
        return Path("/data")

    @property
    def rules_dirs(self) -> list[Path]:
        """Hierarchical .rules directories (system → user → workspace)."""
        return [
            Path("/app/rules"),
            Path.home() / ".milyfe" / "rules",
            self.workspace_path / ".milyfe" / "rules",
        ]

    @property
    def skills_dirs(self) -> list[Path]:
        """Skills directories (user → workspace)."""
        return [
            Path.home() / ".milyfe" / "skills",
            self.workspace_path / ".milyfe" / "skills",
        ]

    @property
    def config_dirs(self) -> list[Path]:
        """Config hierarchy directories."""
        return [
            Path("/app/config"),
            Path.home() / ".milyfe",
            self.workspace_path / ".milyfe",
        ]


# Singleton instance
settings = Settings()
