"""
Circuit breaker pattern for external service resilience.

Implements the three-state circuit breaker (Closed, Open, Half-Open) to
prevent cascading failures when external services (Twilio, SendGrid, FCM,
Ollama) become unavailable.

Usage::

    cb = CircuitBreaker(name="twilio", failure_threshold=5, recovery_timeout=30)
    try:
        result = await cb.call(some_async_function, arg1, arg2)
    except CircuitBreakerOpen:
        # Service is known to be down — fail fast
        handle_fallback()
"""

import asyncio
import time
from enum import Enum
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing — reject calls
    HALF_OPEN = "half_open"  # Testing — allow one call


class CircuitBreakerOpen(Exception):
    """Raised when a call is attempted on an open circuit breaker."""

    def __init__(self, name: str, time_remaining: float) -> None:
        self.name = name
        self.time_remaining = time_remaining
        super().__init__(
            f"Circuit breaker '{name}' is OPEN. "
            f"Recovery in {time_remaining:.1f}s."
        )


class CircuitBreaker:
    """Circuit breaker for external service calls.

    Attributes:
        name: Human-readable service name.
        _failure_threshold: Consecutive failures before opening.
        _recovery_timeout: Seconds to wait before testing (half-open).
        _state: Current circuit state.
        _failure_count: Consecutive failure counter.
        _success_count: Total successful calls.
        _last_failure_time: Timestamp of the most recent failure.
        _state_transitions: Count of state changes (for metrics).
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0.0
        self._state_transitions = 0
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Return the current circuit state, considering recovery timeout."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    async def call(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a function through the circuit breaker.

        Args:
            func: Async callable to execute.
            *args: Positional arguments forwarded to func.
            **kwargs: Keyword arguments forwarded to func.

        Returns:
            The result of func(*args, **kwargs).

        Raises:
            CircuitBreakerOpen: If the circuit is open (fail fast).
        """
        current_state = self.state

        if current_state == CircuitState.OPEN:
            remaining = self._recovery_timeout - (
                time.monotonic() - self._last_failure_time
            )
            raise CircuitBreakerOpen(self.name, max(0.0, remaining))

        try:
            result = await func(*args, **kwargs)
            await self._on_success(current_state)
            return result
        except CircuitBreakerOpen:
            raise  # Don't catch our own exception
        except Exception as exc:
            await self._on_failure(current_state, exc)
            raise

    async def _on_success(self, previous_state: CircuitState) -> None:
        """Handle a successful call."""
        async with self._lock:
            self._success_count += 1

            if previous_state == CircuitState.HALF_OPEN:
                # Test succeeded — close the circuit
                self._transition(CircuitState.CLOSED)
                self._failure_count = 0
                await logger.ainfo(
                    "circuit_breaker_closed",
                    name=self.name,
                    msg="Half-Open → Closed: test call succeeded",
                )
            elif self._state == CircuitState.CLOSED:
                # Reset failure count on success in closed state
                self._failure_count = 0

    async def _on_failure(
        self, previous_state: CircuitState, exc: Exception
    ) -> None:
        """Handle a failed call."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if previous_state == CircuitState.HALF_OPEN:
                # Test failed — reopen the circuit
                self._transition(CircuitState.OPEN)
                await logger.awarning(
                    "circuit_breaker_reopened",
                    name=self.name,
                    error=str(exc),
                    msg="Half-Open → Open: test call failed",
                )
            elif (
                self._state == CircuitState.CLOSED
                and self._failure_count >= self._failure_threshold
            ):
                # Too many failures — open the circuit
                self._transition(CircuitState.OPEN)
                await logger.awarning(
                    "circuit_breaker_opened",
                    name=self.name,
                    failure_count=self._failure_count,
                    threshold=self._failure_threshold,
                    msg="Closed → Open: failure threshold exceeded",
                )

    def _transition(self, new_state: CircuitState) -> None:
        """Transition to a new state and increment counter."""
        self._state = new_state
        self._state_transitions += 1

    def get_metrics(self) -> dict[str, Any]:
        """Return circuit breaker metrics for observability.

        Returns:
            Dict with state, counters, and timing info.
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self._failure_threshold,
            "recovery_timeout": self._recovery_timeout,
            "last_failure_time": self._last_failure_time,
            "state_transitions": self._state_transitions,
        }

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._state_transitions += 1


# ── Global Registry ──────────────────────────────────────────────────────


_registry: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
) -> CircuitBreaker:
    """Get or create a named circuit breaker from the global registry.

    Args:
        name: Service name (e.g., 'twilio', 'sendgrid', 'fcm', 'ollama').
        failure_threshold: Failures before opening.
        recovery_timeout: Seconds before testing recovery.

    Returns:
        The CircuitBreaker instance for the given name.
    """
    if name not in _registry:
        _registry[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    return _registry[name]


def get_all_circuit_breakers() -> dict[str, CircuitBreaker]:
    """Return all registered circuit breakers."""
    return dict(_registry)


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers (useful in tests)."""
    _registry.clear()
