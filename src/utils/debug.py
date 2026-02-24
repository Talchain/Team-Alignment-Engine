"""Debugging utilities for TAE development and troubleshooting.

Provides tools for:
- Trace ID correlation across distributed calls
- Request/response inspection
- State snapshots for reproducing issues
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID, uuid4
from contextvars import ContextVar
from functools import wraps
import inspect

logger = logging.getLogger(__name__)

# Context variable for trace ID (request-scoped)
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


# ============================================================================
# TRACE ID CORRELATION
# ============================================================================


def set_trace_id(trace_id: str) -> None:
    """
    Set trace ID for current request context.

    Args:
        trace_id: Trace ID from X-Request-ID header or generated
    """
    trace_id_var.set(trace_id)
    logger.debug(f"Trace ID set: {trace_id}")


def get_trace_id() -> Optional[str]:
    """
    Get current trace ID from context.

    Returns:
        Current trace ID or None if not set
    """
    return trace_id_var.get()


def get_or_create_trace_id() -> str:
    """
    Get existing trace ID or create new one.

    Returns:
        Trace ID (existing or newly created)
    """
    trace_id = get_trace_id()
    if not trace_id:
        trace_id = f"tae-{uuid4()}"
        set_trace_id(trace_id)
    return trace_id


def trace_correlation(func):
    """
    Decorator to add trace ID to function logging.

    Usage:
        @trace_correlation
        async def my_function():
            # All logs will include trace_id
            pass
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        trace_id = get_or_create_trace_id()
        extra = {"trace_id": trace_id}

        logger.info(
            f"[{trace_id}] Entering {func.__name__}",
            extra=extra,
        )

        try:
            result = await func(*args, **kwargs)
            logger.info(
                f"[{trace_id}] Exiting {func.__name__}",
                extra=extra,
            )
            return result
        except Exception as e:
            logger.error(
                f"[{trace_id}] Error in {func.__name__}: {e}",
                extra=extra,
                exc_info=True,
            )
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        trace_id = get_or_create_trace_id()
        extra = {"trace_id": trace_id}

        logger.info(
            f"[{trace_id}] Entering {func.__name__}",
            extra=extra,
        )

        try:
            result = func(*args, **kwargs)
            logger.info(
                f"[{trace_id}] Exiting {func.__name__}",
                extra=extra,
            )
            return result
        except Exception as e:
            logger.error(
                f"[{trace_id}] Error in {func.__name__}: {e}",
                extra=extra,
                exc_info=True,
            )
            raise

    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


# ============================================================================
# REQUEST/RESPONSE INSPECTION
# ============================================================================


class RequestInspector:
    """Inspector for HTTP requests and responses."""

    def __init__(self, max_body_length: int = 10000):
        """
        Initialize request inspector.

        Args:
            max_body_length: Maximum length of request/response body to log
        """
        self.max_body_length = max_body_length
        self.inspection_log: List[Dict[str, Any]] = []

    async def inspect_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Inspect and log HTTP request details.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            headers: Request headers
            body: Request body
            trace_id: Optional trace ID

        Returns:
            Inspection record
        """
        trace_id = trace_id or get_or_create_trace_id()

        # Sanitize sensitive headers
        safe_headers = self._sanitize_headers(headers or {})

        # Truncate large bodies
        safe_body = self._truncate_body(body)

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id,
            "type": "request",
            "method": method,
            "url": url,
            "headers": safe_headers,
            "body": safe_body,
        }

        self.inspection_log.append(record)

        logger.debug(
            f"[{trace_id}] Request: {method} {url}",
            extra={
                "trace_id": trace_id,
                "method": method,
                "url": url,
                "headers": safe_headers,
            },
        )

        return record

    async def inspect_response(
        self,
        status_code: int,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        duration_ms: Optional[float] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Inspect and log HTTP response details.

        Args:
            status_code: HTTP status code
            headers: Response headers
            body: Response body
            duration_ms: Request duration in milliseconds
            trace_id: Optional trace ID

        Returns:
            Inspection record
        """
        trace_id = trace_id or get_or_create_trace_id()

        safe_headers = self._sanitize_headers(headers or {})
        safe_body = self._truncate_body(body)

        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "trace_id": trace_id,
            "type": "response",
            "status_code": status_code,
            "headers": safe_headers,
            "body": safe_body,
            "duration_ms": duration_ms,
        }

        self.inspection_log.append(record)

        logger.debug(
            f"[{trace_id}] Response: {status_code} ({duration_ms}ms)",
            extra={
                "trace_id": trace_id,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )

        return record

    def get_inspection_log(
        self,
        trace_id: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get inspection log entries.

        Args:
            trace_id: Filter by trace ID (optional)
            limit: Maximum number of entries to return

        Returns:
            List of inspection records
        """
        log = self.inspection_log

        if trace_id:
            log = [entry for entry in log if entry.get("trace_id") == trace_id]

        if limit:
            log = log[-limit:]

        return log

    def clear_log(self) -> None:
        """Clear inspection log."""
        self.inspection_log.clear()

    def export_log(self, filepath: str) -> None:
        """
        Export inspection log to JSON file.

        Args:
            filepath: Path to output file
        """
        with open(filepath, "w") as f:
            json.dump(self.inspection_log, f, indent=2)

        logger.info(f"Inspection log exported to {filepath}")

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive headers from logging."""
        sensitive_keys = ["authorization", "x-api-key", "cookie", "password"]
        return {
            k: "***REDACTED***" if k.lower() in sensitive_keys else v
            for k, v in headers.items()
        }

    def _truncate_body(self, body: Any) -> Any:
        """Truncate large request/response bodies."""
        if body is None:
            return None

        if isinstance(body, str):
            if len(body) > self.max_body_length:
                return body[: self.max_body_length] + "...[TRUNCATED]"
            return body

        if isinstance(body, (dict, list)):
            body_str = json.dumps(body)
            if len(body_str) > self.max_body_length:
                return body_str[: self.max_body_length] + "...[TRUNCATED]"
            return body

        return str(body)[: self.max_body_length]


# Global request inspector instance
request_inspector = RequestInspector()


# ============================================================================
# STATE SNAPSHOTS
# ============================================================================


class StateSnapshot:
    """Capture application state for debugging and reproduction."""

    def __init__(self):
        """Initialize state snapshot."""
        self.snapshots: Dict[str, Dict[str, Any]] = {}

    async def capture(
        self,
        snapshot_id: Optional[str] = None,
        session_id: Optional[str] = None,
        include_db: bool = False,
        include_redis: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Capture current application state.

        Args:
            snapshot_id: Unique snapshot identifier (auto-generated if not provided)
            session_id: Session ID to capture state for
            include_db: Whether to include database state
            include_redis: Whether to include Redis cache state
            metadata: Additional metadata to include

        Returns:
            Snapshot data
        """
        snapshot_id = snapshot_id or f"snapshot-{uuid4()}"
        trace_id = get_or_create_trace_id()

        snapshot = {
            "snapshot_id": snapshot_id,
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "metadata": metadata or {},
            "context": {},
        }

        # Capture basic context
        snapshot["context"]["trace_id"] = trace_id

        # Conditionally capture database state
        if include_db and session_id:
            snapshot["database"] = await self._capture_db_state(session_id)

        # Conditionally capture Redis state
        if include_redis and session_id:
            snapshot["redis"] = await self._capture_redis_state(session_id)

        # Store snapshot
        self.snapshots[snapshot_id] = snapshot

        logger.info(
            f"State snapshot captured: {snapshot_id}",
            extra={
                "snapshot_id": snapshot_id,
                "trace_id": trace_id,
                "session_id": session_id,
            },
        )

        return snapshot

    async def _capture_db_state(self, session_id: str) -> Dict[str, Any]:
        """
        Capture database state for session.

        Args:
            session_id: Session ID

        Returns:
            Database state summary
        """
        # This would query the database for session-related records
        # Placeholder implementation
        return {
            "session_id": session_id,
            "note": "DB state capture not yet implemented",
        }

    async def _capture_redis_state(self, session_id: str) -> Dict[str, Any]:
        """
        Capture Redis cache state for session.

        Args:
            session_id: Session ID

        Returns:
            Redis cache summary
        """
        # This would query Redis for session-related keys
        # Placeholder implementation
        return {
            "session_id": session_id,
            "note": "Redis state capture not yet implemented",
        }

    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve snapshot by ID.

        Args:
            snapshot_id: Snapshot identifier

        Returns:
            Snapshot data or None if not found
        """
        return self.snapshots.get(snapshot_id)

    def list_snapshots(self) -> List[str]:
        """
        List all snapshot IDs.

        Returns:
            List of snapshot IDs
        """
        return list(self.snapshots.keys())

    def export_snapshot(self, snapshot_id: str, filepath: str) -> None:
        """
        Export snapshot to JSON file.

        Args:
            snapshot_id: Snapshot identifier
            filepath: Path to output file

        Raises:
            KeyError: If snapshot not found
        """
        snapshot = self.snapshots[snapshot_id]

        with open(filepath, "w") as f:
            json.dump(snapshot, f, indent=2)

        logger.info(
            f"Snapshot exported: {snapshot_id} -> {filepath}",
            extra={"snapshot_id": snapshot_id, "filepath": filepath},
        )

    def clear_snapshots(self) -> None:
        """Clear all snapshots."""
        count = len(self.snapshots)
        self.snapshots.clear()
        logger.info(f"Cleared {count} snapshots")


# Global state snapshot instance
state_snapshot = StateSnapshot()


# ============================================================================
# DIAGNOSTIC HELPERS
# ============================================================================


def format_exception_for_debugging(
    exc: Exception,
    include_locals: bool = True,
) -> Dict[str, Any]:
    """
    Format exception with debugging information.

    Args:
        exc: Exception to format
        include_locals: Whether to include local variables

    Returns:
        Formatted exception data
    """
    import traceback
    import sys

    exc_type, exc_value, exc_traceback = sys.exc_info()

    # Get traceback as string
    tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    # Extract stack frames
    frames = []
    tb = exc_traceback
    while tb is not None:
        frame = tb.tb_frame
        frame_info = {
            "filename": frame.f_code.co_filename,
            "function": frame.f_code.co_name,
            "lineno": tb.tb_lineno,
        }

        if include_locals:
            # Sanitize local variables
            frame_info["locals"] = {
                k: str(v)[:200] for k, v in frame.f_locals.items()
                if not k.startswith("_")
            }

        frames.append(frame_info)
        tb = tb.tb_next

    return {
        "exception_type": exc_type.__name__ if exc_type else "Unknown",
        "exception_message": str(exc_value),
        "traceback": tb_str,
        "frames": frames,
        "trace_id": get_trace_id(),
        "timestamp": datetime.utcnow().isoformat(),
    }


def log_with_context(
    message: str,
    level: str = "INFO",
    **context: Any,
) -> None:
    """
    Log message with additional context.

    Args:
        message: Log message
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        **context: Additional context fields
    """
    trace_id = get_or_create_trace_id()

    extra = {
        "trace_id": trace_id,
        **context,
    }

    log_func = getattr(logger, level.lower(), logger.info)
    log_func(f"[{trace_id}] {message}", extra=extra)
