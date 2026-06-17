"""Circuit Breaker — Automatic failure isolation for external services."""

import asyncio
import time
from enum import Enum
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for external service calls."""

    def __init__(self, name: str, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0
        self.success_count = 0

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit half-open", service=self.name)
            else:
                raise CircuitOpenError(f"Circuit breaker open for {self.name}")

        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            logger.info("Circuit closed", service=self.name)

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning("Circuit opened", service=self.name, failures=self.failure_count)

    def get_status(self) -> dict:
        return {"name": self.name, "state": self.state.value, "failures": self.failure_count}


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Pre-configured breakers
ollama_breaker = CircuitBreaker("ollama", failure_threshold=3, recovery_timeout=15.0)
chromadb_breaker = CircuitBreaker("chromadb", failure_threshold=5, recovery_timeout=30.0)
redis_breaker = CircuitBreaker("redis", failure_threshold=5, recovery_timeout=30.0)
