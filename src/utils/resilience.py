"""Resilience patterns for fault tolerance and performance optimization.

Provides circuit breaker and timeout utilities to prevent cascading failures
and ensure graceful degradation of capabilities.
"""

import logging
import asyncio
from typing import Optional, Any, Callable, TypeVar, Dict
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Failure threshold exceeded, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures.

    Monitors failure rates and opens the circuit when threshold is exceeded.
    Provides automatic recovery testing after a timeout period.

    States:
    - CLOSED: Normal operation (success rate above threshold)
    - OPEN: Fast-fail mode (success rate below threshold)
    - HALF_OPEN: Recovery testing (allow limited requests through)

    Example:
        >>> breaker = CircuitBreaker(
        ...     name="d5_analytics",
        ...     failure_threshold=0.5,
        ...     recovery_timeout=30.0,
        ... )
        >>> result = await breaker.call(analytics_engine.analyze_trends, org_id)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: float = 0.5,
        min_requests: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_requests: int = 3,
    ):
        """Initialize circuit breaker.

        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Failure rate to trigger open (0.0-1.0)
            min_requests: Minimum requests before evaluating threshold
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_requests: Max requests to allow in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.min_requests = min_requests
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests

        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_requests = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate."""
        total = self._failure_count + self._success_count
        if total == 0:
            return 0.0
        return self._failure_count / total

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self._last_failure_time is None:
            return False

        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _transition_to_half_open(self) -> None:
        """Transition from OPEN to HALF_OPEN state."""
        self._state = CircuitState.HALF_OPEN
        self._half_open_requests = 0
        logger.info(
            "circuit_breaker_half_open",
            extra={"name": self.name, "state": self._state},
        )

    def _transition_to_open(self) -> None:
        """Transition to OPEN state (circuit trips)."""
        self._state = CircuitState.OPEN
        self._last_failure_time = datetime.utcnow()
        logger.warning(
            "circuit_breaker_opened",
            extra={
                "name": self.name,
                "failure_rate": self.failure_rate,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
            },
        )

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state (circuit resets)."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        logger.info(
            "circuit_breaker_closed",
            extra={"name": self.name},
        )

    def _record_success(self) -> None:
        """Record a successful request."""
        self._success_count += 1

        if self._state == CircuitState.HALF_OPEN:
            # Success in half-open state - may transition to closed
            if self._half_open_requests >= self.half_open_max_requests:
                self._transition_to_closed()

    def _record_failure(self) -> None:
        """Record a failed request."""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()

        total_requests = self._failure_count + self._success_count

        # Check if we should open the circuit
        if self._state == CircuitState.CLOSED:
            if (
                total_requests >= self.min_requests
                and self.failure_rate >= self.failure_threshold
            ):
                self._transition_to_open()

        elif self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open state reopens the circuit
            self._transition_to_open()

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        fallback: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            fallback: Optional fallback value if circuit is open
            **kwargs: Keyword arguments for func

        Returns:
            Result from func or fallback value

        Raises:
            CircuitBreakerOpenError: If circuit is open and no fallback provided
        """
        # Check if we should attempt reset
        if self._state == CircuitState.OPEN and self._should_attempt_reset():
            self._transition_to_half_open()

        # Fast-fail if circuit is open
        if self._state == CircuitState.OPEN:
            logger.warning(
                "circuit_breaker_rejected_request",
                extra={"name": self.name, "state": self._state},
            )
            if fallback is not None:
                return fallback
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN (failure rate: {self.failure_rate:.2%})"
            )

        # Track half-open requests
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_requests += 1

        # Execute request
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result

        except Exception as e:
            self._record_failure()
            logger.error(
                "circuit_breaker_request_failed",
                extra={
                    "name": self.name,
                    "error": str(e),
                    "failure_rate": self.failure_rate,
                },
            )
            raise

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        logger.info("circuit_breaker_manual_reset", extra={"name": self.name})
        self._transition_to_closed()

    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_rate": self.failure_rate,
            "total_requests": self._failure_count + self._success_count,
            "last_failure_time": (
                self._last_failure_time.isoformat()
                if self._last_failure_time
                else None
            ),
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open and request is rejected."""

    pass


class TimeoutError(Exception):
    """Raised when operation exceeds timeout."""

    pass


async def with_timeout(
    coro: Any,
    timeout_seconds: float,
    operation_name: str = "operation",
) -> Any:
    """Execute coroutine with timeout.

    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds
        operation_name: Name for logging

    Returns:
        Result from coroutine

    Raises:
        TimeoutError: If operation exceeds timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        logger.warning(
            "operation_timeout",
            extra={
                "operation": operation_name,
                "timeout_seconds": timeout_seconds,
            },
        )
        raise TimeoutError(
            f"{operation_name} exceeded timeout of {timeout_seconds}s"
        )


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: float = 0.5,
    min_requests: int = 5,
    recovery_timeout: float = 30.0,
) -> CircuitBreaker:
    """Get or create a circuit breaker instance.

    Args:
        name: Circuit breaker name
        failure_threshold: Failure rate to trigger open (0.0-1.0)
        min_requests: Minimum requests before evaluating threshold
        recovery_timeout: Seconds to wait before attempting recovery

    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            min_requests=min_requests,
            recovery_timeout=recovery_timeout,
        )

    return _circuit_breakers[name]


def reset_all_circuit_breakers() -> None:
    """Reset all circuit breakers (useful for testing)."""
    for breaker in _circuit_breakers.values():
        breaker.reset()

    logger.info(
        "all_circuit_breakers_reset",
        extra={"count": len(_circuit_breakers)},
    )
