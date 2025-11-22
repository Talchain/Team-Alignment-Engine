"""Enhanced structured logging configuration for TAE.

Provides JSON-formatted logs with context enrichment including:
- trace_id
- session_id
- user_id (pseudonymous)
- operation
- duration_ms

Supports different log levels for different environments.
"""

import logging
import logging.config
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from contextvars import ContextVar

from src.config import settings


# Context variables for request-scoped logging context
logging_context_var: ContextVar[Dict[str, Any]] = ContextVar("logging_context", default={})


class ContextEnrichedFormatter(logging.Formatter):
    """
    JSON formatter that enriches logs with request context.

    Automatically includes trace_id, session_id, user_id, and other
    contextual information from context variables.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON with context enrichment.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Base log structure
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context from context variable
        context = logging_context_var.get({})
        log_data.update(context)

        # Add extra fields from LogRecord
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "method"):
            log_data["method"] = record.method

        # Add function and line info for DEBUG level
        if record.levelno == logging.DEBUG:
            log_data["function"] = record.funcName
            log_data["line"] = record.lineno
            log_data["module"] = record.module

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info),
            }

        # Add stack info if present
        if record.stack_info:
            log_data["stack_info"] = record.stack_info

        return json.dumps(log_data, default=str)


class PlainTextFormatter(logging.Formatter):
    """
    Human-readable formatter for development.

    Format: [TIMESTAMP] [LEVEL] [trace_id] logger: message
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as plain text."""
        timestamp = datetime.utcnow().isoformat()[:19]
        level = record.levelname[:4].upper()

        # Get trace ID if available
        trace_id = getattr(record, "trace_id", None)
        trace_str = f"[{trace_id[:12]}]" if trace_id else "[no-trace]"

        # Base format
        msg = f"[{timestamp}] [{level}] {trace_str} {record.name}: {record.getMessage()}"

        # Add exception if present
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        return msg


def set_logging_context(**kwargs: Any) -> None:
    """
    Set logging context for current request.

    Args:
        **kwargs: Context fields to set (trace_id, session_id, user_id, etc.)

    Example:
        set_logging_context(
            trace_id="req-abc123",
            session_id="session-456",
            user_id="user-789",
        )
    """
    current = logging_context_var.get({})
    current.update(kwargs)
    logging_context_var.set(current)


def clear_logging_context() -> None:
    """Clear logging context (typically at end of request)."""
    logging_context_var.set({})


def get_logging_context() -> Dict[str, Any]:
    """
    Get current logging context.

    Returns:
        Dictionary of current context fields
    """
    return logging_context_var.get({})


def configure_logging() -> None:
    """
    Configure logging based on environment settings.

    - Development: Plain text format, DEBUG level
    - Staging/Production: JSON format, INFO level
    """
    # Determine log format based on environment
    use_json = settings.environment in ["staging", "production"]

    # Determine log level
    log_level = settings.log_level.upper()

    # Configure logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": ContextEnrichedFormatter,
            },
            "plain": {
                "()": PlainTextFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "json" if use_json else "plain",
                "stream": sys.stdout,
            },
        },
        "loggers": {
            "src": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn.access": {
                "level": "INFO" if settings.environment == "production" else "DEBUG",
                "handlers": ["console"],
                "propagate": False,
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",  # Suppress SQL logs in production
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": log_level,
            "handlers": ["console"],
        },
    }

    logging.config.dictConfig(logging_config)

    # Log configuration complete
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configured",
        extra={
            "environment": settings.environment,
            "log_level": log_level,
            "format": "json" if use_json else "plain",
        },
    )


# Utility functions for structured logging
def log_operation(
    logger: logging.Logger,
    operation: str,
    level: str = "INFO",
    **context: Any,
) -> None:
    """
    Log an operation with context.

    Args:
        logger: Logger instance
        operation: Operation name
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        **context: Additional context fields
    """
    log_func = getattr(logger, level.lower(), logger.info)
    log_func(
        f"Operation: {operation}",
        extra={"operation": operation, **context},
    )


def log_api_request(
    logger: logging.Logger,
    method: str,
    endpoint: str,
    status_code: int,
    duration_ms: float,
    **context: Any,
) -> None:
    """
    Log API request with standardized format.

    Args:
        logger: Logger instance
        method: HTTP method
        endpoint: API endpoint
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **context: Additional context (trace_id, user_id, etc.)
    """
    level = "WARNING" if status_code >= 400 else "INFO"
    log_func = getattr(logger, level.lower())

    log_func(
        f"{method} {endpoint} {status_code} {duration_ms:.2f}ms",
        extra={
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "duration_ms": duration_ms,
            **context,
        },
    )


def log_external_call(
    logger: logging.Logger,
    service: str,
    endpoint: str,
    duration_ms: float,
    success: bool,
    **context: Any,
) -> None:
    """
    Log external service call.

    Args:
        logger: Logger instance
        service: Service name (ISL, CEE, etc.)
        endpoint: Called endpoint
        duration_ms: Call duration in milliseconds
        success: Whether call succeeded
        **context: Additional context
    """
    level = "INFO" if success else "WARNING"
    status = "success" if success else "failed"

    log_func = getattr(logger, level.lower())
    log_func(
        f"External call to {service}/{endpoint} {status} ({duration_ms:.2f}ms)",
        extra={
            "service": service,
            "endpoint": endpoint,
            "duration_ms": duration_ms,
            "success": success,
            **context,
        },
    )


def log_degraded_mode(
    logger: logging.Logger,
    reason: str,
    **context: Any,
) -> None:
    """
    Log degraded mode activation.

    Args:
        logger: Logger instance
        reason: Reason for degraded mode (redis_unavailable, isl_timeout, etc.)
        **context: Additional context
    """
    logger.warning(
        f"Degraded mode activated: {reason}",
        extra={
            "degraded": True,
            "degraded_reason": reason,
            **context,
        },
    )


def log_cache_operation(
    logger: logging.Logger,
    operation: str,
    cache_key: str,
    hit: bool,
    **context: Any,
) -> None:
    """
    Log cache operation.

    Args:
        logger: Logger instance
        operation: Operation type (get, set, delete)
        cache_key: Cache key
        hit: Whether cache hit (for get operations)
        **context: Additional context
    """
    logger.debug(
        f"Cache {operation}: {cache_key} ({'hit' if hit else 'miss'})",
        extra={
            "operation": f"cache_{operation}",
            "cache_key": cache_key,
            "cache_hit": hit,
            **context,
        },
    )
