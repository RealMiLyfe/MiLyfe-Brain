"""
MiLyfe Brain - Circuit Breaker Service

Implements the Circuit Breaker pattern to prevent cascading failures.
States: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (testing recovery).

Pre-built breakers for: ollama, chromadb, redis.
"""
from __future__ import annotations

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation — requests flow through
    OPEN = "open"          # Failing — requests are rejected immediately
    HALF_OPEN = "half_open"  # Testing — limited requests to check recovery


class CircuitBreaker:
    """
    Circuit Breaker implementation.

    Parameters:
        name: Identifier for this breaker.
        failure_threshold: Number of failures before opening the circuit.
        recovery_timeout: Seconds to wait before trying again (HALF_OPEN).
        success_threshold: Successes in HALF_OPEN needed to close the circuit.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_failure_time: float = 0.0
        self._last_state_change: float = time.time()

    @property
    def state(self) -> CircuitState:
        """Current circuit state (may transition from OPEN to HALF_OPEN)."""
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._transition(CircuitState.HALF_OPEN)
        return self._state

    @property
    def is_available(self) -> bool:
        """Whether the circuit allows requests."""
        return self.state != CircuitState.OPEN

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async or sync callable to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.

        Returns:
            The function result.

        Raises:
            CircuitBreakerOpen: If circuit is OPEN.
            Exception: Any exception from func (after recording failure).
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpen(
                f"Circuit breaker '{self.name}' is OPEN. "
                f"Recovery in {self.recovery_timeout - (time.time() - self._last_failure_time):.1f}s"
            )

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

    def _on_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._transition(CircuitState.CLOSED)
                logger.info("Circuit breaker '%s' recovered (CLOSED)", self.name)
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN reopens the circuit
            self._transition(CircuitState.OPEN)
            logger.warning("Circuit breaker '%s' reopened (HALF_OPEN -> OPEN)", self.name)
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._transition(CircuitState.OPEN)
                logger.warning(
                    "Circuit breaker '%s' opened after %d failures",
                    self.name, self._failure_count,
                )

    def _transition(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0

        logger.debug(
            "Circuit breaker '%s': %s -> %s",
            self.name, old_state.value, new_state.value,
        )

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._transition(CircuitState.CLOSED)
        self._failure_count = 0
        self._success_count = 0

    def get_info(self) -> Dict[str, Any]:
        """Get circuit breaker status info."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
            "last_state_change": self._last_state_change,
        }


class CircuitBreakerOpen(Exception):
    """Raised when a circuit breaker is in OPEN state."""
    pass


# ============================================================
# Pre-built Circuit Breakers
# ============================================================

breakers: Dict[str, CircuitBreaker] = {
    "ollama": CircuitBreaker(
        name="ollama",
        failure_threshold=3,
        recovery_timeout=30.0,
        success_threshold=2,
    ),
    "chromadb": CircuitBreaker(
        name="chromadb",
        failure_threshold=5,
        recovery_timeout=60.0,
        success_threshold=2,
    ),
    "redis": CircuitBreaker(
        name="redis",
        failure_threshold=5,
        recovery_timeout=45.0,
        success_threshold=2,
    ),
}
