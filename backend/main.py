"""MiLyfe Brain — FastAPI Application Entry Point.

Middleware stack, lifespan events, and route registration.
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from config import settings

logger = structlog.get_logger()


# ─── Middleware ───────────────────────────────────────────────────────────────


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests larger than configured max size."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_size_mb * 1024 * 1024:
            return Response(content="Request too large", status_code=413)
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per IP."""

    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Clean old entries
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window_seconds]

        if len(self.requests[client_ip]) >= self.max_requests:
            return Response(content="Rate limit exceeded", status_code=429)

        self.requests[client_ip].append(now)
        return await call_next(request)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Optional API key enforcement."""

    async def dispatch(self, request: Request, call_next):
        if not settings.auth_enabled:
            return await call_next(request)

        # Skip health check
        if request.url.path == "/health":
            return await call_next(request)

        # Skip WebSocket upgrade
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if api_key != settings.api_key:
            return Response(content="Unauthorized", status_code=401)

        return await call_next(request)


# ─── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application startup and shutdown sequence."""
    logger.info("Starting MiLyfe Brain...")

    # 1. Initialize database
    from memory.database import init_db
    await init_db()
    logger.info("Database initialized")

    # 2. Start queue processor
    from services.queue_manager import queue_manager
    app.state.queue_task = asyncio.create_task(queue_manager.process_loop())
    logger.info("Queue processor started")

    # 3. Start scheduler
    from services.scheduler_service import scheduler_service
    app.state.scheduler_task = asyncio.create_task(scheduler_service.run())
    logger.info("Scheduler started")

    # 4. Start autonomous daemon (non-fatal)
    try:
        from services.daemon import daemon_service
        app.state.daemon_task = asyncio.create_task(daemon_service.run())
        logger.info("Daemon started")
    except Exception as e:
        logger.warning("Daemon startup failed (non-fatal)", error=str(e))

    # 5. Initialize workspace git (non-fatal)
    try:
        from services.workspace_git import workspace_git
        await workspace_git.init()
        logger.info("Workspace git initialized")
    except Exception as e:
        logger.warning("Workspace git init failed (non-fatal)", error=str(e))

    # 6. Wire notification service (non-fatal)
    try:
        from services.notification_service import notification_service
        notification_service.start()
        logger.info("Notification service started")
    except Exception as e:
        logger.warning("Notification service startup failed (non-fatal)", error=str(e))

    # 7. Health check Ollama (non-fatal)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                logger.info("Ollama connected", model_count=len(models))
            else:
                logger.warning("Ollama responded with non-200", status=resp.status_code)
    except Exception as e:
        logger.warning("Ollama not reachable (non-fatal)", error=str(e))

    # 8. ChromaDB telemetry monkey-patch
    try:
        import chromadb
        chromadb.config.Settings(anonymized_telemetry=False)
    except Exception:
        pass

    logger.info("MiLyfe Brain started successfully", port=8200)

    yield

    # Shutdown
    logger.info("Shutting down MiLyfe Brain...")

    # Cancel background tasks
    for task_name in ["queue_task", "scheduler_task", "daemon_task"]:
        task = getattr(app.state, task_name, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    logger.info("MiLyfe Brain shut down")


# ─── Application ──────────────────────────────────────────────────────────────


app = FastAPI(
    title="MiLyfe Brain",
    description="AI Agent Swarm Orchestration Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware stack (order matters — outermost first)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_per_minute,
    window_seconds=60,
)
app.add_middleware(APIKeyAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_allow_all else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ───────────────────────────────────────────────────────────────────


from api.routes import (
    agents,
    chat,
    daemon,
    documents,
    download,
    export_import,
    filesystem,
    health,
    logs,
    notifications,
    playbooks,
    queue,
    scheduler,
    selftest,
    settings_api,
    streaming,
    tasks,
    tokens,
    workspace,
)

app.include_router(health.router)
app.include_router(playbooks.router, prefix="/api/playbooks", tags=["Playbooks"])
app.include_router(agents.router, prefix="/api/agents", tags=["Agents"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(streaming.router, prefix="/api/stream", tags=["Streaming"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["Settings"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(selftest.router, prefix="/api/selftest", tags=["Self-Test"])
app.include_router(workspace.router, prefix="/api/workspace", tags=["Workspace"])
app.include_router(download.router, prefix="/api/download", tags=["Download"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["Scheduler"])
app.include_router(tokens.router, prefix="/api/tokens", tags=["Tokens"])
app.include_router(queue.router, prefix="/api/queue", tags=["Queue"])
app.include_router(filesystem.router, prefix="/api/filesystem", tags=["Filesystem"])
app.include_router(daemon.router, prefix="/api/brain", tags=["Brain"])
app.include_router(export_import.router, prefix="/api/playbooks/io", tags=["Export/Import"])
