"""Request timeout middleware to prevent long-running requests."""

import asyncio
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_504_GATEWAY_TIMEOUT

from src.config import settings

logger = logging.getLogger(__name__)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce request timeouts."""

    def __init__(self, app, timeout_seconds: int = None):
        """
        Initialize timeout middleware.

        Args:
            app: FastAPI application
            timeout_seconds: Request timeout in seconds (default: from settings)
        """
        super().__init__(app)
        self.timeout_seconds = timeout_seconds or settings.request_timeout

    async def dispatch(self, request: Request, call_next):
        """Process request with timeout."""
        request_id = getattr(request.state, "request_id", None)

        try:
            # Use asyncio.wait_for to enforce timeout
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds
            )
            return response

        except asyncio.TimeoutError:
            logger.warning(
                "Request timeout",
                extra={
                    "request_id": request_id,
                    "path": request.url.path,
                    "timeout_seconds": self.timeout_seconds,
                }
            )
            return JSONResponse(
                status_code=HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "schema": "error.v1",
                    "code": "REQUEST_TIMEOUT",
                    "message": f"Request exceeded timeout of {self.timeout_seconds} seconds",
                    "request_id": request_id,
                    "suggested_action": "retry_with_simpler_request",
                },
            )
