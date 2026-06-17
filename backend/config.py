"""Pydantic Settings — environment-driven configuration."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Service connections
    chroma_host: str = Field(default="chromadb", description="ChromaDB hostname")
    chroma_port: int = Field(default=8000, description="ChromaDB port")
    redis_host: str = Field(default="redis", description="Redis hostname")
    redis_port: int = Field(default=6379, description="Redis port")

    # Ollama
    ollama_base_url: str = Field(default="http://host.docker.internal:11434", description="Ollama API URL")

    # Models
    default_light_model: str = Field(default="phi3:mini", description="Light/fast model")
    default_heavy_model: str = Field(default="llama3.1:8b", description="Heavy/quality model")
    premium_model: str = Field(default="llama3.1:70b", description="Premium model")

    # Agent config
    max_agents: int = Field(default=10, description="Maximum concurrent agents")
    agent_timeout: int = Field(default=300, description="Agent timeout in seconds")
    max_retries: int = Field(default=3, description="Max retries on failure")

    # Safety
    require_approval_destructive: bool = Field(default=True, description="Require approval for destructive ops")
    require_approval_browsing: bool = Field(default=True, description="Require approval for web browsing")
    require_approval_gui: bool = Field(default=True, description="Require approval for GUI actions")

    # Workspace
    workspace_dir: str = Field(default="/workspace", description="Workspace directory path")
    auto_git_snapshots: bool = Field(default=True, description="Auto git snapshots")

    # Context
    context_summarize_threshold: int = Field(default=32000, description="Token threshold for summarization")

    # Security
    auth_enabled: bool = Field(default=False, description="Enable API key auth")
    api_key: str = Field(default="change-me-to-a-real-secret", description="API key")
    cors_allow_all: bool = Field(default=True, description="Allow all CORS origins")

    # Database
    database_url: str = Field(default="sqlite:////data/milyfe.db", description="Database URL")

    # Rate limiting
    rate_limit_per_minute: int = Field(default=120, description="Requests per minute per IP")
    max_request_size_mb: int = Field(default=10, description="Max request body size in MB")

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
