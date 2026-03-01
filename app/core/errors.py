"""Standardized error response format for all API endpoints.

Every error response from EigenCore follows this structure:
{
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Human-readable description",
        "details": {}  // optional, extra context
    }
}

This replaces FastAPI's default {"detail": "..."} format for consistency
across all endpoints and easier client-side error handling.
"""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# --- Error codes ---

class ErrorCode:
    """Standard error codes used across all endpoints."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    BAD_REQUEST = "BAD_REQUEST"
    RATE_LIMITED = "RATE_LIMITED"


# Map HTTP status codes to default error codes
STATUS_TO_CODE = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL_ERROR,
    501: ErrorCode.NOT_IMPLEMENTED,
}


# --- Response schemas ---

class ErrorBody(BaseModel):
    """Inner error object."""
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error response envelope."""
    error: ErrorBody


# --- Exception handlers ---

def _error_code_for_status(status_code: int) -> str:
    return STATUS_TO_CODE.get(status_code, ErrorCode.INTERNAL_ERROR)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException with standardized format."""
    code = _error_code_for_status(exc.status_code)
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)

    logger.warning(
        "HTTP %d %s: %s %s",
        exc.status_code, code, request.method, request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors with standardized format."""
    errors = exc.errors()
    # Build a human-readable summary
    fields = [
        ".".join(str(loc) for loc in e.get("loc", []))
        for e in errors
    ]
    message = f"Validation failed on: {', '.join(fields)}" if fields else "Validation failed"

    logger.warning(
        "Validation error: %s %s — %s",
        request.method, request.url.path, message,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": ErrorCode.VALIDATION_ERROR,
                "message": message,
                "details": {"validation_errors": errors},
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never leak internals."""
    logger.exception(
        "Unhandled exception: %s %s", request.method, request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "An internal error occurred. Please try again later.",
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all standardized error handlers on a FastAPI app."""
    # StarletteHTTPException is the base; FastAPI's HTTPException extends it.
    # Registering on the base class catches both (including 404 from router).
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
