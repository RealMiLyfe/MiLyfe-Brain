"""Resilience utilities — circuit breakers, timeouts, retries.

Provides reusable patterns for graceful degradation when
external services (Ollama, ChromaDB, Redis) are unavailable.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Generic circuit breaker for any async operation.

    Usage:
        breaker = CircuitBreaker(name="ollama", failure_threshold=3)
        result = await breaker.call(some_async_function, fallback="default")
    """

    name: str
    failure_threshold: int = 3
    recovery_timeout: float = 30.0
    _failure_count: int = field(default=0, init=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _last_success_time: float = field(default=0.0, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    @property
    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_success_time = time.time()

    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker '%s' OPEN after %d failures",
                self.name, self._failure_count,
            )

    async def call(
        self,
        func: Callable,
        *args,
        fallback: Any = None,
        timeout: float = 30.0,
        **kwargs,
    ) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Async callable to execute.
            fallback: Value to return if circuit is open or call fails.
            timeout: Max seconds to wait for the call.

        Returns:
            Function result, or fallback on failure.
        """
        if not self.is_available:
            logger.debug("Circuit '%s' is OPEN, returning fallback", self.name)
            return fallback

        try:
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=timeout)
            self.record_success()
            return result
        except asyncio.TimeoutError:
            self.record_failure()
            logger.warning("Circuit '%s': timeout after %.1fs", self.name, timeout)
            return fallback
        except Exception as e:
            self.record_failure()
            logger.warning("Circuit '%s': error: %s", self.name, e)
            return fallback

    def status(self) -> dict:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "threshold": self.failure_threshold,
            "last_failure": self._last_failure_time,
            "last_success": self._last_success_time,
        }


# ─── Global Circuit Breakers ─────────────────────────────────────────

ollama_breaker = CircuitBreaker(name="ollama", failure_threshold=3, recovery_timeout=30.0)
chromadb_breaker = CircuitBreaker(name="chromadb", failure_threshold=3, recovery_timeout=30.0)
redis_breaker = CircuitBreaker(name="redis", failure_threshold=5, recovery_timeout=15.0)


async def with_timeout(coro, timeout: float, default: Any = None) -> Any:
    """Run a coroutine with a timeout, returning default on timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return default
    except Exception:
        return default
