"""Unified error handling and response mapping."""

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.app.core.logging import log_error


class ErrorResponse(BaseModel):
    """Standardized error response format."""

    error: str
    message: str
    request_id: str | None = None


class BusinessError(Exception):
    """Base class for business logic errors."""

    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ResourceNotFoundError(BusinessError):
    """Raised when a requested resource doesn't exist."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UnauthorizedAccessError(BusinessError):
    """Raised when attempting to access resource owned by another tenant."""

    def __init__(self, resource_type: str):
        super().__init__(
            message=f"Access denied to {resource_type}",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ValidationError(BusinessError):
    """Raised for input validation errors."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class RateLimitError(BusinessError):
    """Raised when rate limit is exceeded."""

    def __init__(self):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    """Handle business logic errors with safe, generic messages."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    log_error(
        request_id=request_id,
        error_type=exc.__class__.__name__,
        error_message=exc.message,
        status_code=exc.status_code,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            message=exc.message,
            request_id=request_id,
        ).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions with safe, generic messages.
    
    NEVER expose tracebacks, database errors, or internal details.
    """
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    log_error(
        request_id=request_id,
        error_type=exc.__class__.__name__,
        error_message=str(exc),
        status_code=500,
    )
    
    # Return generic message - don't leak internal details
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred. Please try again later.",
            request_id=request_id,
        ).model_dump(),
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTP exceptions."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTPException",
            message=exc.detail,
            request_id=request_id,
        ).model_dump(),
    )
