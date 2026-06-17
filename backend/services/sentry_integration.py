"""
Sentry integration for MiLyfe Brain.

Provides error monitoring, performance tracking, and release tracking.

Configuration via environment variables:
    SENTRY_ENABLED=true
    SENTRY_DSN=https://key@sentry.io/project
    SENTRY_ENVIRONMENT=production
    SENTRY_RELEASE=v2.0.0
    SENTRY_TRACES_SAMPLE_RATE=0.1
    SENTRY_PROFILES_SAMPLE_RATE=0.1
"""

import os
from typing import Any, Dict, Optional

SENTRY_ENABLED = os.getenv("SENTRY_ENABLED", "false").lower() == "true"
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

if SENTRY_ENABLED and SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.asyncio import AsyncioIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.httpx import HttpxIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        SENTRY_AVAILABLE = True
    except ImportError:
        SENTRY_AVAILABLE = False
        SENTRY_ENABLED = False
else:
    SENTRY_AVAILABLE = False


class SentryService:
    """Manages Sentry error monitoring integration."""

    def __init__(self):
        self._initialized = False

    def initialize(self):
        """Initialize Sentry SDK with configured options."""
        if not SENTRY_ENABLED or not SENTRY_AVAILABLE or not SENTRY_DSN:
            return

        environment = os.getenv("SENTRY_ENVIRONMENT", "development")
        release = os.getenv("SENTRY_RELEASE", "milyfe-brain@2.0.0")
        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
        profiles_sample_rate = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1"))

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            environment=environment,
            release=release,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            send_default_pii=False,  # Don't send PII
            attach_stacktrace=True,
            include_local_variables=True,
            max_breadcrumbs=50,

            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                HttpxIntegration(),
                AsyncioIntegration(),
                LoggingIntegration(
                    level=None,           # Don't capture logs as breadcrumbs below WARNING
                    event_level="ERROR",  # Capture ERROR+ as events
                ),
            ],

            # Filter sensitive data
            before_send=self._before_send,
            before_send_transaction=self._before_send_transaction,

            # Ignore common non-errors
            ignore_errors=[
                KeyboardInterrupt,
                SystemExit,
                ConnectionResetError,
            ],
        )

        # Set global tags
        sentry_sdk.set_tag("service", "milyfe-brain-backend")
        sentry_sdk.set_tag("version", "2.0.0")

        self._initialized = True

    def _before_send(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter events before sending to Sentry."""
        # Don't send 404 errors
        if "exception" in event:
            for exc in event.get("exception", {}).get("values", []):
                if "404" in exc.get("type", ""):
                    return None

        # Remove sensitive headers
        if "request" in event:
            headers = event["request"].get("headers", {})
            sensitive_keys = ["x-api-key", "authorization", "cookie"]
            for key in sensitive_keys:
                headers.pop(key, None)

        return event

    def _before_send_transaction(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter transactions before sending."""
        # Don't track health check transactions
        transaction = event.get("transaction", "")
        if transaction in ("/health", "/metrics"):
            return None
        return event

    def capture_exception(self, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Capture an exception with optional context."""
        if not self._initialized:
            return

        if context:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_extra(key, value)
                sentry_sdk.capture_exception(error)
        else:
            sentry_sdk.capture_exception(error)

    def capture_message(self, message: str, level: str = "info", context: Optional[Dict[str, Any]] = None):
        """Capture a message event."""
        if not self._initialized:
            return

        if context:
            with sentry_sdk.push_scope() as scope:
                for key, value in context.items():
                    scope.set_extra(key, value)
                sentry_sdk.capture_message(message, level=level)
        else:
            sentry_sdk.capture_message(message, level=level)

    def set_user(self, user_id: str, username: Optional[str] = None):
        """Set the current user context."""
        if not self._initialized:
            return
        sentry_sdk.set_user({"id": user_id, "username": username})

    def set_tag(self, key: str, value: str):
        """Set a global tag."""
        if not self._initialized:
            return
        sentry_sdk.set_tag(key, value)

    def add_breadcrumb(self, message: str, category: str = "custom", level: str = "info", data: Optional[Dict] = None):
        """Add a breadcrumb for debugging context."""
        if not self._initialized:
            return
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {},
        )

    def start_transaction(self, name: str, op: str = "task"):
        """Start a performance transaction."""
        if not self._initialized:
            return None
        return sentry_sdk.start_transaction(name=name, op=op)

    def flush(self, timeout: float = 2.0):
        """Flush pending events."""
        if not self._initialized:
            return
        sentry_sdk.flush(timeout=timeout)


# Singleton instance
sentry = SentryService()
