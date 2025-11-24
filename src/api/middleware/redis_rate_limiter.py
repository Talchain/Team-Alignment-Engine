"""Redis-backed rate limiting middleware for production use."""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from typing import Optional
from jose import jwt, JWTError

from src.config import settings
from src.storage.cache import get_cache

logger = logging.getLogger(__name__)


class RedisRateLimiterMiddleware(BaseHTTPMiddleware):
    """Redis-backed rate limiter using sliding window algorithm.

    PERFORMANCE: Extracts user_id from JWT for per-user rate limiting.
    Falls back to IP-based limiting for unauthenticated requests.
    """

    def __init__(self, app, requests: int = None, window: int = None):
        """
        Initialize Redis rate limiter.

        Args:
            app: FastAPI application
            requests: Max requests per window (default: from settings)
            window: Window size in seconds (default: from settings)
        """
        super().__init__(app)
        self.max_requests = requests or settings.rate_limit_requests
        self.window = window or settings.rate_limit_window

    def _extract_user_id_from_token(self, request: Request) -> Optional[str]:
        """
        Extract user_id from JWT token in Authorization header.

        Args:
            request: Incoming request

        Returns:
            User ID if token is valid, None otherwise
        """
        try:
            # Get Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return None

            # Extract token
            token = auth_header.split(" ")[1]

            # Decode JWT (don't verify - we just need user_id for rate limiting)
            # Verification happens later in auth dependencies
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False}  # Don't verify expiration for rate limiting
            )

            return payload.get("sub")

        except (JWTError, IndexError, AttributeError):
            # Invalid token format - fall back to IP-based limiting
            return None

    async def dispatch(self, request: Request, call_next):
        """Check rate limit and process request using Redis."""
        # Extract user_id from JWT token for per-user rate limiting
        user_id = self._extract_user_id_from_token(request)

        # Fallback to IP-based limiting for unauthenticated requests
        client_ip = request.client.host if request.client else "unknown"
        client_key = f"user:{user_id}" if user_id else f"ip:{client_ip}"

        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        try:
            # Get Redis client
            cache = await get_cache()

            # Rate limiting key
            rate_limit_key = f"rate_limit:{client_key}"
            current_time = time.time()
            window_start = current_time - self.window

            # Use Redis sorted set for sliding window
            # Remove old entries outside the window
            await cache.zremrangebyscore(rate_limit_key, 0, window_start)

            # Count requests in current window
            request_count = await cache.zcard(rate_limit_key)

            # Check rate limit
            if request_count >= self.max_requests:
                request_id = getattr(request.state, "request_id", None)
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "client_key": client_key,
                        "request_count": request_count,
                        "limit": self.max_requests,
                        "request_id": request_id,
                    }
                )
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

            # Add current request to sorted set
            await cache.zadd(rate_limit_key, {str(current_time): current_time})

            # Set expiration on the key (cleanup)
            await cache.expire(rate_limit_key, self.window)

            # Get updated count for headers
            updated_count = await cache.zcard(rate_limit_key)

            # Process request
            response = await call_next(request)
            response.headers["X-Rate-Limit-Limit"] = str(self.max_requests)
            response.headers["X-Rate-Limit-Remaining"] = str(
                max(0, self.max_requests - updated_count)
            )
            response.headers["X-Rate-Limit-Reset"] = str(
                int(current_time + self.window)
            )

            return response

        except Exception as e:
            # If Redis is unavailable, allow the request through with warning
            logger.error(
                "Rate limiter error - allowing request",
                extra={"error": str(e), "client_key": client_key},
                exc_info=True
            )
            # Degrade gracefully - allow request but warn
            response = await call_next(request)
            response.headers["X-Rate-Limit-Status"] = "degraded"
            return response
