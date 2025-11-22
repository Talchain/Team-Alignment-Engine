"""Error handling middleware using error.v1 standard."""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def setup_error_handlers(app: FastAPI) -> None:
    """Set up global error handlers for the application."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle HTTP exceptions with error.v1 format."""
        request_id = getattr(request.state, "request_id", None)

        logger.warning(
            f"HTTP exception: {exc.status_code}",
            extra={
                "request_id": request_id,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "schema": "error.v1",
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": request_id,
                "suggested_action": _get_suggested_action(exc.status_code),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors with error.v1 format."""
        request_id = getattr(request.state, "request_id", None)

        logger.warning(
            "Validation error",
            extra={
                "request_id": request_id,
                "errors": exc.errors(),
                "path": request.url.path,
            },
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "schema": "error.v1",
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
                "request_id": request_id,
                "suggested_action": "check_request_parameters",
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all uncaught exceptions with error.v1 format."""
        request_id = getattr(request.state, "request_id", None)

        logger.error(
            "Unhandled exception",
            extra={
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "error": str(exc),
                "path": request.url.path,
            },
            exc_info=True,
        )

        # Sanitize error message in production
        from src.config import settings
        if settings.environment == "production":
            error_message = "An internal server error occurred. Please contact support."
        else:
            error_message = str(exc)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "schema": "error.v1",
                "code": "INTERNAL_ERROR",
                "message": error_message,
                "request_id": request_id,
                "suggested_action": "contact_support" if settings.environment == "production" else "retry_later",
            },
        )


def _get_suggested_action(status_code: int) -> str:
    """Get suggested action based on status code."""
    actions = {
        400: "check_request_parameters",
        401: "authenticate",
        403: "check_permissions",
        404: "check_resource_id",
        409: "resolve_conflict",
        422: "check_request_parameters",
        429: "retry_with_backoff",
        500: "retry_later",
        503: "retry_later",
    }
    return actions.get(status_code, "contact_support")
