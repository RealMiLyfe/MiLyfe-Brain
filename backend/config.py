"""Pydantic Settings for MiLyfe Brain — env-driven configuration."""

import os
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ─── Core ─────────────────────────────────────────────────────────
    app_name: str = "MiLyfe Brain"
    app_version: str = "2.0.0"
    debug: bool = False

    # ─── Server ───────────────────────────────────────────────────────
    backend_port: int = 8200
    frontend_port: int = 3000

    # ─── Database ─────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:////data/milyfe.db"

    # ─── Redis ────────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379"
    redis_port: int = 6479

    # ─── Ollama / LLM ─────────────────────────────────────────────────
    ollama_base_url: str = "http://host.docker.internal:11434"
    default_light_model: str = "phi3:mini"
    default_heavy_model: str = "llama3.1:8b"
    premium_model: str = "llama3.1:70b"

    # ─── ChromaDB ─────────────────────────────────────────────────────
    chromadb_url: str = "http://chromadb:8000"
    chroma_port: int = 8400

    # ─── Agent Configuration ──────────────────────────────────────────
    max_agents: int = 10
    agent_timeout: int = 300
    max_retries: int = 3
    context_summarize_threshold: int = 32000

    # ─── Safety / Permissions ─────────────────────────────────────────
    require_approval_destructive: bool = True
    require_approval_browsing: bool = True
    require_approval_gui: bool = True

    # ─── Auth ─────────────────────────────────────────────────────────
    auth_enabled: bool = False
    api_key: str = "change-me-to-a-real-secret"

    # ─── CORS ─────────────────────────────────────────────────────────
    cors_allow_all: bool = True
    cors_allowed_origins: str = ""

    # ─── Workspace ────────────────────────────────────────────────────
    workspace_dir: str = "/workspace"
    auto_git_snapshots: bool = True

    # ─── Logging ──────────────────────────────────────────────────────
    log_level: str = "INFO"
    log_format: str = "text"
    log_dir: str = "/data/logs"

    # ─── Telemetry / Monitoring ───────────────────────────────────────
    otel_enabled: bool = False
    sentry_enabled: bool = False
    sentry_dsn: str = ""
    metrics_enabled: bool = True

    # ─── TLS ──────────────────────────────────────────────────────────
    tls_enabled: bool = False

    # ─── Rate Limiting ────────────────────────────────────────────────
    rate_limit_per_minute: int = 120
    max_request_size_mb: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
