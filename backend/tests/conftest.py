"""Pytest fixtures for MiLyfe Brain tests."""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_settings():
    """Mock settings with test values."""
    with patch("config.settings") as mock:
        mock.workspace_dir = "/tmp/test_workspace"
        mock.database_url = "sqlite:///tmp/test_milyfe.db"
        mock.ollama_base_url = "http://localhost:11434"
        mock.default_light_model = "phi3:mini"
        mock.default_heavy_model = "llama3.1:8b"
        mock.premium_model = "llama3.1:70b"
        mock.max_agents = 10
        mock.agent_timeout = 30
        mock.max_retries = 3
        mock.require_approval_destructive = True
        mock.require_approval_browsing = True
        mock.require_approval_gui = True
        mock.auto_git_snapshots = False
        mock.auth_enabled = False
        mock.api_key = "test-key"
        mock.cors_allow_all = True
        mock.rate_limit_per_minute = 120
        mock.max_request_size_mb = 10
        mock.chroma_url = "http://localhost:8400"
        mock.redis_url = "redis://localhost:6379"
        mock.context_summarize_threshold = 32000
        yield mock
