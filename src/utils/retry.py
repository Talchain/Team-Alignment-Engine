"""Retry logic with exponential backoff for external service calls."""

import asyncio
import logging
from typing import TypeVar, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_exponential_backoff(
    max_attempts: int = 4,
    initial_delay: float = 2.0,
    max_delay: float = 16.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying async functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch and retry

    Example:
        @retry_with_exponential_backoff(max_attempts=3)
        async def call_external_service():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            delay = initial_delay

            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            f"Max retry attempts ({max_attempts}) reached for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempts": attempt,
                                "error": str(e),
                            },
                            exc_info=True
                        )
                        raise

                    # Calculate delay with exponential backoff
                    current_delay = min(delay, max_delay)
                    logger.warning(
                        f"Retry attempt {attempt}/{max_attempts} for {func.__name__} "
                        f"after {current_delay}s delay",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "delay_seconds": current_delay,
                            "error": str(e),
                        }
                    )

                    await asyncio.sleep(current_delay)
                    delay *= exponential_base

        return wrapper
    return decorator


def retry_sync(
    max_attempts: int = 4,
    initial_delay: float = 2.0,
    max_delay: float = 16.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying synchronous functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch and retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            import time

            attempt = 0
            delay = initial_delay

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            f"Max retry attempts ({max_attempts}) reached for {func.__name__}",
                            extra={
                                "function": func.__name__,
                                "attempts": attempt,
                                "error": str(e),
                            },
                            exc_info=True
                        )
                        raise

                    current_delay = min(delay, max_delay)
                    logger.warning(
                        f"Retry attempt {attempt}/{max_attempts} for {func.__name__} "
                        f"after {current_delay}s delay",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "delay_seconds": current_delay,
                            "error": str(e),
                        }
                    )

                    time.sleep(current_delay)
                    delay *= exponential_base

        return wrapper
    return decorator
