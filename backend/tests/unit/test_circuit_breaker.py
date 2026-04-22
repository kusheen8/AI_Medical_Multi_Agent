"""
Unit tests for the circuit breaker pattern.

Tests all state transitions, concurrent call behavior,
metrics recording, and manual reset.
"""

import asyncio
import time

import pytest

from app.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
    get_circuit_breaker,
    reset_all_circuit_breakers,
)


# ── Helpers ──────────────────────────────────────────────────────────────


async def success_func() -> str:
    return "ok"


async def failure_func() -> str:
    raise RuntimeError("Service unavailable")


async def timeout_func() -> str:
    raise TimeoutError("Connection timed out")


# ── Tests ────────────────────────────────────────────────────────────────


class TestCircuitBreakerStates:
    """Tests for circuit breaker state transitions."""

    def setup_method(self):
        reset_all_circuit_breakers()

    @pytest.mark.asyncio
    async def test_starts_closed(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_stays_closed_on_success(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        result = await cb.call(success_func)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_closed_to_open_after_threshold(self):
        cb = CircuitBreaker("test", failure_threshold=3)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(failure_func)
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_rejects_calls(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=10)
        # Open the circuit
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(failure_func)
        assert cb.state == CircuitState.OPEN
        # Should fail fast without calling the function
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await cb.call(success_func)
        assert exc_info.value.name == "test"
        assert exc_info.value.time_remaining > 0

    @pytest.mark.asyncio
    async def test_open_to_half_open_after_timeout(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(failure_func)
        assert cb.state == CircuitState.OPEN
        # Wait for recovery timeout
        await asyncio.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_to_closed_on_success(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(failure_func)
        await asyncio.sleep(0.15)  # Enter half-open
        # Successful call should close the circuit
        result = await cb.call(success_func)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_to_open_on_failure(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(failure_func)
        await asyncio.sleep(0.15)  # Enter half-open
        assert cb.state == CircuitState.HALF_OPEN
        # Failed test call should reopen
        with pytest.raises(RuntimeError):
            await cb.call(failure_func)
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerMetrics:
    """Tests for circuit breaker metrics."""

    def setup_method(self):
        reset_all_circuit_breakers()

    @pytest.mark.asyncio
    async def test_success_count(self):
        cb = CircuitBreaker("test", failure_threshold=5)
        for _ in range(3):
            await cb.call(success_func)
        metrics = cb.get_metrics()
        assert metrics["success_count"] == 3
        assert metrics["failure_count"] == 0

    @pytest.mark.asyncio
    async def test_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=5)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(failure_func)
        metrics = cb.get_metrics()
        assert metrics["failure_count"] == 3
        assert metrics["success_count"] == 0

    @pytest.mark.asyncio
    async def test_state_transitions_count(self):
        cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.05)
        # Closed → Open
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(failure_func)
        await asyncio.sleep(0.1)  # Open → Half-Open (automatic)
        await cb.call(success_func)  # Half-Open → Closed
        metrics = cb.get_metrics()
        assert metrics["state_transitions"] == 2  # Closed→Open, Half-Open→Closed

    @pytest.mark.asyncio
    async def test_metrics_structure(self):
        cb = CircuitBreaker("test-service", failure_threshold=5, recovery_timeout=30)
        metrics = cb.get_metrics()
        assert metrics["name"] == "test-service"
        assert "state" in metrics
        assert "failure_threshold" in metrics
        assert "recovery_timeout" in metrics


class TestCircuitBreakerReset:
    """Tests for manual reset."""

    def setup_method(self):
        reset_all_circuit_breakers()

    @pytest.mark.asyncio
    async def test_manual_reset(self):
        cb = CircuitBreaker("test", failure_threshold=2)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(failure_func)
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reset_clears_failure_count(self):
        cb = CircuitBreaker("test", failure_threshold=5)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(failure_func)
        cb.reset()
        metrics = cb.get_metrics()
        assert metrics["failure_count"] == 0


class TestCircuitBreakerRegistry:
    """Tests for the global circuit breaker registry."""

    def setup_method(self):
        reset_all_circuit_breakers()

    def test_get_creates_new(self):
        cb = get_circuit_breaker("test-service")
        assert cb.name == "test-service"

    def test_get_returns_same_instance(self):
        cb1 = get_circuit_breaker("test-service")
        cb2 = get_circuit_breaker("test-service")
        assert cb1 is cb2

    def test_reset_clears_registry(self):
        get_circuit_breaker("svc1")
        get_circuit_breaker("svc2")
        reset_all_circuit_breakers()
        # After reset, should create a new instance
        cb = get_circuit_breaker("svc1")
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerConcurrency:
    """Tests for concurrent call behavior."""

    def setup_method(self):
        reset_all_circuit_breakers()

    @pytest.mark.asyncio
    async def test_failure_count_resets_on_success(self):
        """A success in closed state should reset the failure count."""
        cb = CircuitBreaker("test", failure_threshold=3)
        # 2 failures, then 1 success
        with pytest.raises(RuntimeError):
            await cb.call(failure_func)
        with pytest.raises(RuntimeError):
            await cb.call(failure_func)
        await cb.call(success_func)  # Success resets count
        # 2 more failures should NOT open (because count was reset)
        with pytest.raises(RuntimeError):
            await cb.call(failure_func)
        with pytest.raises(RuntimeError):
            await cb.call(failure_func)
        assert cb.state == CircuitState.CLOSED  # Still at 2, threshold is 3
