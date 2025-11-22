"""Logging middleware for automatic context enrichment.

Automatically sets logging context from request headers and user authentication.
"""

import logging
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.config.logging_config import set_logging_context, clear_logging_context, log_api_request

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic logging context enrichment.

    Sets context variables from request headers and authentication:
    - trace_id from X-Request-ID header
    - user_id from authenticated user
    - session_id from request parameters
    - endpoint and method from request

    Also logs all API requests with duration and status code.
    """

    def __init__(self, app: ASGIApp):
        """Initialize logging middleware."""
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request with logging context enrichment.

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        # Extract trace ID from header or generate new one
        trace_id = request.headers.get("X-Request-ID") or request.headers.get("X-Trace-ID")
        if not trace_id:
            from uuid import uuid4
            trace_id = f"tae-{uuid4()}"

        # Extract session ID from query params or path
        session_id = request.query_params.get("session_id")
        if not session_id and "/sessions/" in request.url.path:
            # Try to extract from path like /api/v1/sessions/{session_id}/...
            path_parts = request.url.path.split("/")
            if "sessions" in path_parts:
                idx = path_parts.index("sessions")
                if len(path_parts) > idx + 1:
                    session_id = path_parts[idx + 1]

        # Extract user ID from authentication (if available)
        user_id = None
        if hasattr(request.state, "user"):
            user = request.state.user
            user_id = getattr(user, "user_id", None)
            if user_id:
                # Pseudonymize user ID for privacy
                user_id = str(user_id)[:8] + "..."

        # Set logging context
        set_logging_context(
            trace_id=trace_id,
            session_id=session_id,
            user_id=user_id,
            method=request.method,
            endpoint=request.url.path,
        )

        # Add trace ID to response header for client correlation
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Add trace ID to response headers
            response.headers["X-Request-ID"] = trace_id

            # Log API request
            log_api_request(
                logger=logger,
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
                trace_id=trace_id,
                session_id=session_id,
                user_id=user_id,
            )

            return response

        except Exception as e:
            # Calculate duration even for errors
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "trace_id": trace_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "duration_ms": duration_ms,
                    "exception": str(e),
                },
                exc_info=True,
            )

            # Re-raise exception to be handled by error middleware
            raise

        finally:
            # Clear logging context at end of request
            clear_logging_context()
