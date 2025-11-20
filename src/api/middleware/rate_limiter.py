"""Rate limiting middleware."""

import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from src.config import settings


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter middleware."""

    def __init__(self, app, requests: int = None, window: int = None):
        """
        Initialize rate limiter.

        Args:
            app: FastAPI application
            requests: Max requests per window (default: from settings)
            window: Window size in seconds (default: from settings)
        """
        super().__init__(app)
        self.max_requests = requests or settings.rate_limit_requests
        self.window = window or settings.rate_limit_window
        self.requests = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        """Check rate limit and process request."""
        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        # Clean up old requests
        current_time = time.time()
        self.requests[client_ip] = [
            req_time
            for req_time in self.requests[client_ip]
            if current_time - req_time < self.window
        ]

        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            request_id = getattr(request.state, "request_id", None)
            return JSONResponse(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "schema": "error.v1",
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded: {self.max_requests} requests per {self.window}s",
                    "request_id": request_id,
                    "suggested_action": "retry_with_backoff",
                },
            )

        # Add current request
        self.requests[client_ip].append(current_time)

        # Process request
        response = await call_next(request)
        response.headers["X-Rate-Limit-Limit"] = str(self.max_requests)
        response.headers["X-Rate-Limit-Remaining"] = str(
            max(0, self.max_requests - len(self.requests[client_ip]))
        )
        response.headers["X-Rate-Limit-Reset"] = str(
            int(current_time + self.window)
        )

        return response
