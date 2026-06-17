"""Pytest configuration and shared fixtures for MiLyfe Brain tests."""

import asyncio
import os
import sys
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Override settings before importing app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///file::memory:?cache=shared"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["WORKSPACE_DIR"] = "/tmp/milyfe-test-workspace"
os.environ["AUTH_ENABLED"] = "false"
os.environ["DEBUG"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    """Create an async HTTP test client for the FastAPI app.
    
    Uses httpx.AsyncClient with the app's TestClient transport.
    """
    from httpx import ASGITransport, AsyncClient
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database session for testing.
    
    Sets up tables, yields the session, then tears down.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    engine = create_async_engine(
        "sqlite+aiosqlite:///file::memory:?cache=shared",
        echo=False,
    )

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def mock_ollama():
    """Mock the Ollama LLM client for tests that don't need real inference.
    
    Returns a mock that simulates Ollama API responses.
    """
    mock = AsyncMock()
    mock.generate = AsyncMock(return_value={
        "model": "phi3:mini",
        "response": "This is a mocked LLM response.",
        "done": True,
        "total_duration": 1000000,
        "eval_count": 10,
    })
    mock.chat = AsyncMock(return_value={
        "model": "phi3:mini",
        "message": {"role": "assistant", "content": "Mocked chat response."},
        "done": True,
    })
    mock.embeddings = AsyncMock(return_value={
        "embedding": [0.1] * 384,
    })
    mock.list = AsyncMock(return_value={
        "models": [
            {"name": "phi3:mini", "size": 2000000000},
            {"name": "llama3.1:8b", "size": 5000000000},
        ]
    })
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client for tests."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.publish = AsyncMock(return_value=1)
    mock.subscribe = AsyncMock()
    return mock


@pytest.fixture
def test_workspace(tmp_path):
    """Create a temporary workspace directory for file operation tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Create some test files
    (workspace / "test.txt").write_text("Hello, World!")
    (workspace / "subdir").mkdir()
    (workspace / "subdir" / "nested.txt").write_text("Nested content")
    
    return workspace


@pytest.fixture
def mock_settings(test_workspace):
    """Override settings for testing."""
    with patch("config.settings") as mock_s:
        mock_s.workspace_dir = str(test_workspace)
        mock_s.database_url = "sqlite+aiosqlite:///file::memory:?cache=shared"
        mock_s.redis_url = "redis://localhost:6379"
        mock_s.auth_enabled = False
        mock_s.api_key = "test-api-key"
        mock_s.rate_limit_per_minute = 120
        mock_s.max_request_size_mb = 10
        mock_s.cors_allow_all = True
        mock_s.debug = True
        mock_s.log_level = "DEBUG"
        mock_s.backend_port = 8200
        mock_s.app_version = "2.0.0-test"
        yield mock_s
