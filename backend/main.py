"""MiLyfe Brain — FastAPI Application Entry Point."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from api import TAGS_METADATA
from config import settings
from memory.database import close_database, init_database

logger = structlog.get_logger()

# Track startup time for uptime calculation
_start_time: float = 0.0


# ============================================================
# Middleware
# ============================================================


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests larger than max_request_size_mb."""

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_size_mb * 1024 * 1024:
            return Response(
                content='{"detail": "Request body too large"}',
                status_code=413,
                media_type="application/json",
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter (per IP, per minute)."""

    def __init__(self, app, max_requests: int = 120):
        super().__init__(app)
        self.max_requests = max_requests
        self._requests: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries
        if client_ip in self._requests:
            self._requests[client_ip] = [t for t in self._requests[client_ip] if now - t < 60]
        else:
            self._requests[client_ip] = []

        if len(self._requests[client_ip]) >= self.max_requests:
            return Response(
                content='{"detail": "Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )

        self._requests[client_ip].append(now)
        return await call_next(request)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Optional API key authentication."""

    async def dispatch(self, request: Request, call_next):
        if not settings.auth_enabled:
            return await call_next(request)

        # Skip auth for health check and docs
        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if api_key != settings.api_key:
            return Response(
                content='{"detail": "Invalid or missing API key"}',
                status_code=401,
                media_type="application/json",
            )
        return await call_next(request)


# ============================================================
# Lifespan
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    global _start_time
    _start_time = time.time()

    logger.info("milyfe_brain_starting", version="1.0.0")

    # 1. Initialize database
    await init_database()
    logger.info("database_initialized")

    # 2. Start queue processor
    try:
        from services.queue_manager import queue_manager
        await queue_manager.start()
        logger.info("queue_manager_started")
    except Exception as e:
        logger.warning("queue_manager_start_failed", error=str(e))

    # 3. Start scheduler service
    try:
        from services.scheduler_service import scheduler_service
        await scheduler_service.start()
        logger.info("scheduler_service_started")
    except Exception as e:
        logger.warning("scheduler_start_failed", error=str(e))

    # 4. Start autonomous daemon (file watcher)
    try:
        from services.daemon import daemon_service
        await daemon_service.start()
        logger.info("daemon_started")
    except Exception as e:
        logger.warning("daemon_start_failed", error=str(e))

    # 5. Initialize workspace git
    try:
        from services.workspace_git import workspace_git
        await workspace_git.initialize()
        logger.info("workspace_git_initialized")
    except Exception as e:
        logger.warning("workspace_git_failed", error=str(e))

    # 6. Wire notification service
    try:
        from services.notification_service import notification_service
        notification_service.initialize()
        logger.info("notification_service_initialized")
    except Exception as e:
        logger.warning("notification_service_failed", error=str(e))

    # 7. Health check Ollama (non-fatal)
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                logger.info("ollama_connected", model_count=len(models))
            else:
                logger.warning("ollama_unhealthy", status=resp.status_code)
    except Exception as e:
        logger.warning("ollama_unavailable", error=str(e))

    logger.info("milyfe_brain_ready")

    yield

    # Shutdown
    logger.info("milyfe_brain_shutting_down")

    try:
        from services.queue_manager import queue_manager
        await queue_manager.stop()
    except Exception:
        pass

    try:
        from services.scheduler_service import scheduler_service
        await scheduler_service.stop()
    except Exception:
        pass

    try:
        from services.daemon import daemon_service
        await daemon_service.stop()
    except Exception:
        pass

    await close_database()
    logger.info("milyfe_brain_stopped")


# ============================================================
# Application
# ============================================================

app = FastAPI(
    title="MiLyfe Brain",
    description="100% local AI agent swarm orchestration platform",
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
)

# --- Middleware Stack (order matters: last added = first executed) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_allow_all else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyAuthMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=settings.rate_limit_per_minute)
app.add_middleware(RequestSizeLimitMiddleware)


# ============================================================
# Route Registration
# ============================================================


def register_routes():
    """Register all API route modules."""
    from api.routes.health import router as health_router
    from api.routes.playbooks import router as playbooks_router
    from api.routes.agents import router as agents_router
    from api.routes.chat import router as chat_router
    from api.routes.streaming import router as streaming_router
    from api.routes.settings_api import router as settings_router
    from api.routes.documents import router as documents_router
    from api.routes.selftest import router as selftest_router
    from api.routes.workspace import router as workspace_router
    from api.routes.download import router as download_router
    from api.routes.notifications import router as notifications_router
    from api.routes.logs import router as logs_router
    from api.routes.scheduler import router as scheduler_router
    from api.routes.tokens import router as tokens_router
    from api.routes.queue import router as queue_router
    from api.routes.filesystem import router as filesystem_router
    from api.routes.daemon import router as daemon_router
    from api.routes.export_import import router as export_import_router
    from api.routes.tasks import router as tasks_router
    from api.routes.brain import router as brain_router

    app.include_router(health_router)
    app.include_router(playbooks_router, prefix="/api/playbooks", tags=["playbooks"])
    app.include_router(agents_router, prefix="/api/agents", tags=["agents"])
    app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
    app.include_router(streaming_router, prefix="/api/stream", tags=["streaming"])
    app.include_router(settings_router, prefix="/api/settings", tags=["settings"])
    app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
    app.include_router(selftest_router, prefix="/api/selftest", tags=["selftest"])
    app.include_router(workspace_router, prefix="/api/workspace", tags=["workspace"])
    app.include_router(download_router, prefix="/api/download", tags=["download"])
    app.include_router(notifications_router, prefix="/api/notifications", tags=["notifications"])
    app.include_router(logs_router, prefix="/api/logs", tags=["logs"])
    app.include_router(scheduler_router, prefix="/api/scheduler", tags=["scheduler"])
    app.include_router(tokens_router, prefix="/api/tokens", tags=["tokens"])
    app.include_router(queue_router, prefix="/api/queue", tags=["queue"])
    app.include_router(filesystem_router, prefix="/api/filesystem", tags=["filesystem"])
    app.include_router(daemon_router, prefix="/api/brain/daemon", tags=["daemon"])
    app.include_router(export_import_router, prefix="/api/playbooks/io", tags=["export_import"])
    app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
    app.include_router(brain_router, prefix="/api/brain", tags=["brain"])


register_routes()


# ============================================================
# Global utility
# ============================================================


def get_uptime() -> float:
    """Return uptime in seconds."""
    return time.time() - _start_time if _start_time else 0.0
