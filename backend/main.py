"""
MiLyfe Brain - FastAPI Application Entry Point

Production-ready application with middleware, lifespan management,
and comprehensive route registration.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, Optional, Tuple

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from api import TAGS_METADATA
from config import settings
from memory.database import close_database, init_database

logger = logging.getLogger(__name__)

# Application start time for uptime tracking
_start_time: float = 0.0


def get_uptime() -> float:
    """Get application uptime in seconds."""
    if _start_time == 0.0:
        return 0.0
    return time.time() - _start_time


# ============================================================
# Middleware Classes
# ============================================================


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests exceeding the configured size limit."""

    def __init__(self, app: Any, max_size_mb: int = 10) -> None:
        super().__init__(app)
        self.max_size_bytes = max_size_mb * 1024 * 1024

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_size_bytes:
            return JSONResponse(
                status_code=413,
                content={"detail": f"Request body too large. Maximum size: {settings.max_request_size_mb}MB"},
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per client IP."""

    def __init__(self, app: Any, requests_per_minute: int = 120) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self._requests: Dict[str, list] = defaultdict(list)
        self._last_cleanup: float = time.time()

    def _cleanup(self) -> None:
        """Remove expired entries older than 60 seconds."""
        now = time.time()
        if now - self._last_cleanup < 30:
            return
        self._last_cleanup = now
        cutoff = now - 60
        expired_keys = []
        for ip, timestamps in self._requests.items():
            self._requests[ip] = [t for t in timestamps if t > cutoff]
            if not self._requests[ip]:
                expired_keys.append(ip)
        for key in expired_keys:
            del self._requests[key]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Periodic cleanup
        self._cleanup()

        # Remove timestamps older than 60 seconds for this IP
        cutoff = now - 60
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > cutoff
        ]

        # Check rate limit
        if len(self._requests[client_ip]) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please try again later."},
            )

        # Record this request
        self._requests[client_ip].append(now)

        return await call_next(request)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Optional API key authentication middleware."""

    # Paths that bypass authentication
    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.auth_enabled:
            return await call_next(request)

        # Skip auth for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        # Check API key
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if not api_key or api_key != settings.api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key."},
            )

        return await call_next(request)


# ============================================================
# Lifespan Management
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    global _start_time
    _start_time = time.time()

    logger.info("MiLyfe Brain starting up...")

    # --- Startup ---
    try:
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Database initialization error (non-fatal): %s", str(e))

    try:
        from services.queue_manager import queue_manager
        await queue_manager.start()
        logger.info("Queue manager started")
    except Exception as e:
        logger.warning("Queue manager start failed (non-fatal): %s", str(e))

    try:
        from services.scheduler_service import scheduler_service
        await scheduler_service.start()
        logger.info("Scheduler service started")
    except Exception as e:
        logger.warning("Scheduler service start failed (non-fatal): %s", str(e))

    try:
        from services.daemon import daemon
        await daemon.start()
        logger.info("Daemon started")
    except Exception as e:
        logger.warning("Daemon start failed (non-fatal): %s", str(e))

    try:
        from services.workspace_git import workspace_git
        await workspace_git.initialize()
        logger.info("Workspace git initialized")
    except Exception as e:
        logger.warning("Workspace git init failed (non-fatal): %s", str(e))

    try:
        from services.notification_service import notification_service
        await notification_service.initialize()
        logger.info("Notification service initialized")
    except Exception as e:
        logger.warning("Notification service init failed (non-fatal): %s", str(e))

    # Non-fatal: check Ollama connectivity
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                logger.info("Ollama connection verified")
            else:
                logger.warning("Ollama returned status %d", resp.status_code)
    except Exception as e:
        logger.warning("Ollama not reachable (non-fatal): %s", str(e))

    logger.info("MiLyfe Brain startup complete on port %d", settings.backend_port)

    yield

    # --- Shutdown ---
    logger.info("MiLyfe Brain shutting down...")

    try:
        from services.daemon import daemon
        await daemon.stop()
    except Exception as e:
        logger.warning("Daemon stop error: %s", str(e))

    try:
        from services.scheduler_service import scheduler_service
        await scheduler_service.stop()
    except Exception as e:
        logger.warning("Scheduler stop error: %s", str(e))

    try:
        from services.queue_manager import queue_manager
        await queue_manager.stop()
    except Exception as e:
        logger.warning("Queue manager stop error: %s", str(e))

    try:
        await close_database()
    except Exception as e:
        logger.warning("Database close error: %s", str(e))

    logger.info("MiLyfe Brain shutdown complete")


# ============================================================
# Route Registration
# ============================================================


def register_routes(app: FastAPI) -> None:
    """Import and register all API route modules."""
    from api.routes import (  # noqa: F401 - dynamic imports
        playbooks,
        agents,
        chat,
        tasks,
        streaming,
        health,
        settings as settings_routes,
        documents,
        selftest,
        workspace,
        download,
        notifications,
        logs,
        scheduler,
        tokens,
        queue,
        filesystem,
        daemon,
        export_import,
        brain,
    )

    app.include_router(playbooks.router, prefix="/api/playbooks", tags=["playbooks"])
    app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
    app.include_router(streaming.router, prefix="/api/streaming", tags=["streaming"])
    app.include_router(health.router, prefix="", tags=["health"])
    app.include_router(settings_routes.router, prefix="/api/settings", tags=["settings"])
    app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
    app.include_router(selftest.router, prefix="/api/selftest", tags=["selftest"])
    app.include_router(workspace.router, prefix="/api/workspace", tags=["workspace"])
    app.include_router(download.router, prefix="/api/download", tags=["download"])
    app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
    app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
    app.include_router(scheduler.router, prefix="/api/scheduler", tags=["scheduler"])
    app.include_router(tokens.router, prefix="/api/tokens", tags=["tokens"])
    app.include_router(queue.router, prefix="/api/queue", tags=["queue"])
    app.include_router(filesystem.router, prefix="/api/filesystem", tags=["filesystem"])
    app.include_router(daemon.router, prefix="/api/daemon", tags=["daemon"])
    app.include_router(export_import.router, prefix="/api/export-import", tags=["export_import"])
    app.include_router(brain.router, prefix="/api/brain", tags=["brain"])


# ============================================================
# Application Factory
# ============================================================


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="MiLyfe Brain",
        description="Local-only AI agent swarm orchestration platform",
        version="0.1.0",
        openapi_tags=TAGS_METADATA,
        lifespan=lifespan,
    )

    # --- Middleware (order matters: last added = first executed) ---

    # CORS - must be added last (executed first)
    if settings.cors_allow_all:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[f"http://localhost:3000", f"http://localhost:{settings.backend_port}"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # API Key Authentication
    app.add_middleware(APIKeyAuthMiddleware)

    # Rate Limiting
    app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)

    # Request Size Limit
    app.add_middleware(RequestSizeLimitMiddleware, max_size_mb=settings.max_request_size_mb)

    # --- Register Routes ---
    register_routes(app)

    return app


# Create the application instance
app = create_app()
