"""
Structured logging configuration with file rotation for MiLyfe Brain.

Features:
- JSON structured logging for production
- Console colored output for development
- Rotating file handler (10MB per file, 5 backups)
- Log correlation with OpenTelemetry trace IDs
- Separate error log file
- Configurable per-module log levels

Configuration via environment variables:
    LOG_LEVEL=INFO
    LOG_FORMAT=json (json|text)
    LOG_DIR=/data/logs
    LOG_FILE_MAX_BYTES=10485760 (10MB)
    LOG_FILE_BACKUP_COUNT=5
    LOG_STDOUT=true
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key in ("agent_id", "agent_role", "playbook_id", "action_type",
                    "tool_name", "user_id", "session_id", "request_id"):
            value = getattr(record, key, None)
            if value:
                log_data[key] = value

        # Add OpenTelemetry trace context
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span and span.is_recording():
                ctx = span.get_span_context()
                log_data["trace_id"] = format(ctx.trace_id, "032x")
                log_data["span_id"] = format(ctx.span_id, "016x")
        except (ImportError, Exception):
            pass

        # Add duration if present
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored console formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Build prefix
        prefix = f"{color}{timestamp} [{record.levelname:>8}]{self.RESET}"
        module = f"\033[90m{record.name}\033[0m"

        # Extra context
        extras = []
        for key in ("agent_role", "playbook_id", "tool_name"):
            value = getattr(record, key, None)
            if value:
                extras.append(f"{key}={value}")
        extra_str = f" \033[90m({', '.join(extras)})\033[0m" if extras else ""

        message = f"{prefix} {module}: {record.getMessage()}{extra_str}"

        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"

        return message


def setup_logging(
    level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_dir: Optional[str] = None,
):
    """Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format (json, text)
        log_dir: Directory for log files
    """
    level = level or os.getenv("LOG_LEVEL", "INFO")
    log_format = log_format or os.getenv("LOG_FORMAT", "text")
    log_dir = log_dir or os.getenv("LOG_DIR", "/data/logs")
    log_stdout = os.getenv("LOG_STDOUT", "true").lower() == "true"
    max_bytes = int(os.getenv("LOG_FILE_MAX_BYTES", "10485760"))  # 10MB
    backup_count = int(os.getenv("LOG_FILE_BACKUP_COUNT", "5"))

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # ─── Console Handler ──────────────────────────────────────────────
    if log_stdout:
        console_handler = logging.StreamHandler(sys.stdout)
        if log_format == "json":
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(ColoredFormatter())
        console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
        root_logger.addHandler(console_handler)

    # ─── File Handlers ────────────────────────────────────────────────
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Main application log (rotating)
    app_log_file = log_path / "milyfe-brain.log"
    file_handler = RotatingFileHandler(
        app_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(file_handler)

    # Error-only log (separate file for quick error review)
    error_log_file = log_path / "milyfe-brain-errors.log"
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)

    # Agent activity log
    agent_log_file = log_path / "agent-activity.log"
    agent_handler = RotatingFileHandler(
        agent_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    agent_handler.setFormatter(JSONFormatter())
    agent_handler.setLevel(logging.INFO)
    agent_logger = logging.getLogger("milyfe.agents")
    agent_logger.addHandler(agent_handler)

    # Security/audit log
    audit_log_file = log_path / "audit.log"
    audit_handler = RotatingFileHandler(
        audit_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    audit_handler.setFormatter(JSONFormatter())
    audit_handler.setLevel(logging.INFO)
    audit_logger = logging.getLogger("milyfe.audit")
    audit_logger.addHandler(audit_handler)

    # ─── Per-module levels ────────────────────────────────────────────
    module_levels = {
        "uvicorn": "WARNING",
        "uvicorn.access": "WARNING",
        "sqlalchemy.engine": "WARNING",
        "httpx": "WARNING",
        "httpcore": "WARNING",
        "milyfe.agents": "INFO",
        "milyfe.audit": "INFO",
        "milyfe.tools": "INFO",
    }

    for module_name, module_level in module_levels.items():
        logging.getLogger(module_name).setLevel(getattr(logging, module_level))

    # Log startup
    root_logger.info(
        "Logging initialized",
        extra={
            "log_level": level,
            "log_format": log_format,
            "log_dir": log_dir,
            "log_files": [
                str(app_log_file),
                str(error_log_file),
                str(agent_log_file),
                str(audit_log_file),
            ],
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a named logger with the milyfe prefix."""
    return logging.getLogger(f"milyfe.{name}")
