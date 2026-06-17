"""MiLyfe Brain — FastAPI Application Entry Point."""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from services.logging_config import get_logger, setup_logging

# Setup logging first
setup_logging(level=settings.log_level, log_format=settings.log_format, log_dir=settings.log_dir)
logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan — startup and shutdown."""
    logger.info("Starting MiLyfe Brain v%s", settings.app_version)

    # 1. Initialize database
    try:
        from memory.database import init_db
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")

    # 1.5. Register tools and wire agent factory
    try:
        from tools import register_all_tools, tool_registry
        from agents.factory import get_agent_factory
        register_all_tools()
        logger.info("Tool registry loaded: %d tools", tool_registry.count())

        # Wire tool executor into agent factory
        factory = get_agent_factory()

        async def _execute_tool(name: str, arguments: dict) -> str:
            """Bridge function: agent tool calls → tool registry execution."""
            return await tool_registry.execute(name, arguments)

        factory.set_tool_executor(_execute_tool)
        logger.info("Agent factory wired to tool registry")
    except Exception as e:
        logger.error(f"Tool/agent wiring failed: {e}")

    # 2. Start queue processor
    try:
        from services.queue_manager import queue_manager
        asyncio.create_task(queue_manager.start())
        logger.info("Queue processor started")
    except Exception as e:
        logger.warning(f"Queue processor failed to start: {e}")

    # 3. Start scheduler
    try:
        from services.scheduler_service import scheduler
        asyncio.create_task(scheduler.start())
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler failed to start: {e}")

    # 4. Start daemon (file watcher)
    try:
        from services.daemon import daemon_service
        asyncio.create_task(daemon_service.start())
        logger.info("Daemon started")
    except Exception as e:
        logger.warning(f"Daemon failed to start: {e}")

    # 5. Initialize workspace git
    try:
        from services.workspace_git import init_workspace_git
        await init_workspace_git()
    except Exception as e:
        logger.warning(f"Workspace git init failed: {e}")

    # 6. Initialize telemetry
    if settings.otel_enabled:
        try:
            from services.telemetry import telemetry
            telemetry.initialize(app)
            logger.info("OpenTelemetry initialized")
        except Exception as e:
            logger.warning(f"Telemetry init failed: {e}")

    # 7. Initialize Sentry
    if settings.sentry_enabled:
        try:
            from services.sentry_integration import sentry
            sentry.initialize()
            logger.info("Sentry initialized")
        except Exception as e:
            logger.warning(f"Sentry init failed: {e}")

    # 8. Health check Ollama
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                logger.info(f"Ollama connected. Models: {models[:5]}")
            else:
                logger.warning("Ollama responded but no models found")
    except Exception:
        logger.warning("Ollama not reachable (non-fatal)")

    # 9. ChromaDB telemetry patch
    try:
        import chromadb
        chromadb.config.Settings(anonymized_telemetry=False)
    except Exception:
        pass

    app.state.start_time = time.time()
    logger.info("MiLyfe Brain ready on port %d", settings.backend_port)

    yield

    # Shutdown — graceful cleanup
    logger.info("Shutting down MiLyfe Brain")

    # Cancel running playbooks gracefully
    try:
        from services.queue_manager import queue_manager
        queue_manager.stop()
        logger.info("Queue manager stopped")
    except Exception as e:
        logger.debug("Queue stop: %s", e)

    try:
        from services.daemon import daemon_service
        daemon_service.stop()
        logger.info("Daemon stopped")
    except Exception as e:
        logger.debug("Daemon stop: %s", e)

    # Retire all active agents
    try:
        from agents.factory import get_agent_factory
        factory = get_agent_factory()
        retired = await factory.retire_all()
        if retired:
            logger.info("Retired %d agents on shutdown", retired)
    except Exception as e:
        logger.debug("Agent retirement: %s", e)

    logger.info("MiLyfe Brain shutdown complete")


# ─── App Creation ─────────────────────────────────────────────────────

app = FastAPI(
    title="MiLyfe Brain",
    description="AI Agent Swarm Orchestration Platform",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ─── Middleware ───────────────────────────────────────────────────────

# Request size limit
@app.middleware("http")
async def request_size_limit(request: Request, call_next):
    """Limit request body size to prevent abuse."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.max_request_size_mb * 1024 * 1024:
        return Response(status_code=413, content="Request too large")
    return await call_next(request)


# Rate limiting
_rate_limit_store: dict = {}


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Simple IP-based rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - 60

    # Clean old entries
    requests = _rate_limit_store.get(client_ip, [])
    requests = [t for t in requests if t > window_start]

    if len(requests) >= settings.rate_limit_per_minute:
        return Response(status_code=429, content="Rate limit exceeded")

    requests.append(now)
    _rate_limit_store[client_ip] = requests
    return await call_next(request)


# API Key auth (optional)
@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    """Optional API key authentication."""
    if not settings.auth_enabled:
        return await call_next(request)

    # Skip auth for health check and docs
    if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json", "/metrics"):
        return await call_next(request)

    api_key = request.headers.get("X-API-Key", "")
    if api_key != settings.api_key:
        return Response(status_code=401, content='{"detail":"Invalid API key"}',
                        media_type="application/json")
    return await call_next(request)


# CORS
cors_origins = ["*"] if settings.cors_allow_all else (
    [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
    or ["http://localhost:3000", "http://localhost:8200"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ──────────────────────────────────────────────────────────

from api.routes import (
    playbooks, agents, chat, tasks, streaming, health,
    settings_api, documents, selftest, workspace, download,
    notifications, logs, scheduler, tokens, queue,
    filesystem, daemon, export_import,
)

app.include_router(health.router)
app.include_router(playbooks.router, prefix="/api/playbooks", tags=["Playbooks"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(streaming.router, prefix="/api/stream", tags=["Streaming"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["Settings"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(selftest.router, prefix="/api/selftest", tags=["Health"])
app.include_router(workspace.router, prefix="/api/workspace", tags=["Workspace"])
app.include_router(download.router, prefix="/api/download", tags=["Workspace"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["Scheduler"])
app.include_router(tokens.router, prefix="/api/tokens", tags=["Tokens"])
app.include_router(queue.router, prefix="/api/queue", tags=["Queue"])
app.include_router(filesystem.router, prefix="/api/filesystem", tags=["Workspace"])
app.include_router(daemon.router, prefix="/api/brain", tags=["Brain"])
app.include_router(export_import.router, prefix="/api/playbooks/io", tags=["Playbooks"])

# Metrics endpoint
if settings.metrics_enabled:
    from services.prometheus_metrics import get_metrics_route
    app.include_router(get_metrics_route())
