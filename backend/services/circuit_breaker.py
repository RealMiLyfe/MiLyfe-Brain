"""MiLyfe Brain — Circuit Breaker for External Services."""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Callable, Dict

import structlog

logger = structlog.get_logger()


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Automatic failure isolation for external services."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time > self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
        return self._state

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker."""
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitOpenError(f"Circuit '{self.name}' is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Record successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info("circuit_closed", name=self.name)
        else:
            self._failure_count = 0

    def _on_failure(self):
        """Record failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning("circuit_opened", name=self.name, failures=self._failure_count)

    def reset(self):
        """Manually reset the circuit."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


# Pre-built circuit breakers for external services
breakers: Dict[str, CircuitBreaker] = {
    "ollama": CircuitBreaker("ollama", failure_threshold=3, recovery_timeout=15.0),
    "chromadb": CircuitBreaker("chromadb", failure_threshold=5, recovery_timeout=30.0),
    "redis": CircuitBreaker("redis", failure_threshold=5, recovery_timeout=20.0),
}
