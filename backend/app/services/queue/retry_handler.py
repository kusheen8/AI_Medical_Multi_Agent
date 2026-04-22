"""
Notification retry handler with exponential backoff.

Manages retry attempts for failed notification deliveries with
configurable backoff timing and failure-type differentiation.

Retry schedule (default):
- Attempt 1: +5s
- Attempt 2: +10s
- Attempt 3: +20s
- After all attempts: move to DLQ
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger(__name__)


class FailureType(str, Enum):
    """Classification of notification failures for retry strategy."""

    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    NETWORK_ERROR = "network_error"
    PROVIDER_ERROR = "provider_error"
    INVALID_RECIPIENT = "invalid_recipient"
    UNKNOWN = "unknown"


# Non-retryable failure types (don't waste retries)
_NON_RETRYABLE = {FailureType.AUTH_ERROR, FailureType.INVALID_RECIPIENT}

# Extended delay multiplier for rate-limited failures
_RATE_LIMIT_MULTIPLIER = 3.0


class RetryResult:
    """Result of a retry-managed operation.

    Attributes:
        success: Whether the operation eventually succeeded.
        attempts: Total number of attempts made.
        result: The successful result (if any).
        last_error: The last error encountered.
        failure_type: Classification of the last failure.
        sent_to_dlq: Whether the item was moved to DLQ.
    """

    def __init__(
        self,
        success: bool = False,
        attempts: int = 0,
        result: Any = None,
        last_error: str = "",
        failure_type: FailureType = FailureType.UNKNOWN,
        sent_to_dlq: bool = False,
    ) -> None:
        self.success = success
        self.attempts = attempts
        self.result = result
        self.last_error = last_error
        self.failure_type = failure_type
        self.sent_to_dlq = sent_to_dlq


class NotificationRetryHandler:
    """Manages retry logic for notification delivery attempts.

    Attributes:
        _max_attempts: Maximum retry attempts before DLQ.
        _base_delay: Base delay in seconds for first retry.
        _multiplier: Delay multiplier for exponential backoff.
        _dlq_callback: Optional callback to invoke when sending to DLQ.
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 5.0,
        multiplier: float = 2.0,
        dlq_callback: Callable[..., Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._multiplier = multiplier
        self._dlq_callback = dlq_callback

    def get_delay(self, attempt: int, failure_type: FailureType = FailureType.UNKNOWN) -> float:
        """Calculate the delay before the next retry attempt.

        Args:
            attempt: The current attempt number (0-indexed).
            failure_type: Type of failure (affects delay strategy).

        Returns:
            Delay in seconds before retrying.
        """
        delay = self._base_delay * (self._multiplier ** attempt)

        # Rate-limited failures get extra delay
        if failure_type == FailureType.RATE_LIMIT:
            delay *= _RATE_LIMIT_MULTIPLIER

        return delay

    def is_retryable(self, failure_type: FailureType) -> bool:
        """Check if a failure type is worth retrying.

        Args:
            failure_type: The type of failure.

        Returns:
            True if the failure is retryable.
        """
        return failure_type not in _NON_RETRYABLE

    async def execute_with_retry(
        self,
        operation: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        item_id: str = "",
        **kwargs: Any,
    ) -> RetryResult:
        """Execute an async operation with retry logic.

        Args:
            operation: The async callable to execute.
            *args: Positional arguments for the operation.
            item_id: Identifier for logging and DLQ tracking.
            **kwargs: Keyword arguments for the operation.

        Returns:
            RetryResult with the outcome of all attempts.
        """
        last_error = ""
        last_failure_type = FailureType.UNKNOWN
        actual_attempts = 0

        for attempt in range(self._max_attempts):
            actual_attempts = attempt + 1
            try:
                result = await operation(*args, **kwargs)

                await logger.ainfo(
                    "retry_success",
                    item_id=item_id,
                    attempt=actual_attempts,
                    max_attempts=self._max_attempts,
                )

                return RetryResult(
                    success=True,
                    attempts=actual_attempts,
                    result=result,
                )

            except Exception as exc:
                last_error = str(exc)
                last_failure_type = self._classify_error(exc)

                await logger.awarning(
                    "retry_attempt_failed",
                    item_id=item_id,
                    attempt=actual_attempts,
                    max_attempts=self._max_attempts,
                    failure_type=last_failure_type.value,
                    error=last_error,
                )

                # Don't retry non-retryable failures
                if not self.is_retryable(last_failure_type):
                    await logger.awarning(
                        "retry_non_retryable_failure",
                        item_id=item_id,
                        failure_type=last_failure_type.value,
                    )
                    break

                # Wait before next attempt (unless it's the last attempt)
                if attempt < self._max_attempts - 1:
                    delay = self.get_delay(attempt, last_failure_type)
                    await logger.ainfo(
                        "retry_waiting",
                        item_id=item_id,
                        delay_seconds=delay,
                        next_attempt=attempt + 2,
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted or aborted — move to DLQ
        sent_to_dlq = False
        if self._dlq_callback is not None:
            try:
                await self._dlq_callback(item_id, last_error, actual_attempts)
                sent_to_dlq = True
                await logger.awarning(
                    "retry_sent_to_dlq",
                    item_id=item_id,
                    attempts=actual_attempts,
                    failure_type=last_failure_type.value,
                )
            except Exception:
                await logger.aerror(
                    "retry_dlq_callback_error",
                    item_id=item_id,
                    exc_info=True,
                )

        return RetryResult(
            success=False,
            attempts=actual_attempts,
            last_error=last_error,
            failure_type=last_failure_type,
            sent_to_dlq=sent_to_dlq,
        )

    @staticmethod
    def _classify_error(exc: Exception) -> FailureType:
        """Classify an exception into a FailureType for retry strategy.

        Args:
            exc: The exception to classify.

        Returns:
            The classified FailureType.
        """
        error_msg = str(exc).lower()

        if "timeout" in error_msg or "timed out" in error_msg:
            return FailureType.TIMEOUT
        elif "rate limit" in error_msg or "429" in error_msg or "too many" in error_msg:
            return FailureType.RATE_LIMIT
        elif "auth" in error_msg or "401" in error_msg or "403" in error_msg:
            return FailureType.AUTH_ERROR
        elif "connection" in error_msg or "network" in error_msg or "dns" in error_msg:
            return FailureType.NETWORK_ERROR
        elif "invalid" in error_msg and ("recipient" in error_msg or "address" in error_msg):
            return FailureType.INVALID_RECIPIENT
        elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
            return FailureType.PROVIDER_ERROR
        else:
            return FailureType.UNKNOWN
