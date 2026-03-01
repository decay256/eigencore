"""
Request validation middleware for EigenCore API.

Provides:
- Consistent error response format for validation errors (422)
- Request body size limiting
- Content-Type enforcement for JSON endpoints
- Structured logging for all validation failures
"""

import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Max request body size: 1MB
MAX_BODY_SIZE = 1 * 1024 * 1024


def _format_validation_errors(errors: list[dict]) -> list[dict]:
    """Normalize validation errors into a consistent shape."""
    formatted = []
    for err in errors:
        formatted.append({
            "field": " -> ".join(str(loc) for loc in err.get("loc", [])),
            "message": err.get("msg", "Unknown validation error"),
            "type": err.get("type", "unknown"),
        })
    return formatted


def register_validation_handlers(app: FastAPI) -> None:
    """Register exception handlers for validation errors on the FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError):
        errors = _format_validation_errors(exc.errors())
        logger.warning(
            "Request validation failed: %s %s — %d error(s): %s",
            request.method,
            request.url.path,
            len(errors),
            errors,
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "details": errors,
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError):
        errors = _format_validation_errors(exc.errors())
        logger.warning(
            "Pydantic validation failed: %s %s — %s",
            request.method,
            request.url.path,
            errors,
        )
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Data validation failed",
                "details": errors,
            },
        )


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces request-level validation rules:
    - Body size limit (rejects oversized payloads with 413)
    - Content-Type check for POST/PUT/PATCH (must be JSON or form)
    - Logs request timing at DEBUG level
    """

    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        method = request.method
        path = request.url.path

        # Skip non-API routes (health, root, docs)
        if not path.startswith("/api/"):
            return await call_next(request)

        # --- Body size check ---
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_SIZE:
            logger.warning(
                "Request too large: %s %s content-length=%s",
                method, path, content_length,
            )
            return JSONResponse(
                status_code=413,
                content={
                    "error": "payload_too_large",
                    "message": f"Request body exceeds maximum size of {MAX_BODY_SIZE} bytes",
                },
            )

        # --- Content-Type check for body methods ---
        if method in ("POST", "PUT", "PATCH"):
            ct = (request.headers.get("content-type") or "").lower()
            allowed = ("application/json", "application/x-www-form-urlencoded", "multipart/form-data")
            if ct and not any(ct.startswith(a) for a in allowed):
                logger.warning(
                    "Unsupported Content-Type: %s %s content-type=%s",
                    method, path, ct,
                )
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": "unsupported_media_type",
                        "message": f"Content-Type must be one of: {', '.join(allowed)}",
                    },
                )

        response = await call_next(request)

        duration = time.monotonic() - start
        logger.debug(
            "Request: %s %s → %d (%.3fs)",
            method, path, response.status_code, duration,
        )

        return response
