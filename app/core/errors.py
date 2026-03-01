"""
Standardized error response handling for EigenCore API.

Implements the error-response contract (contracts/error-response.yaml).
All API errors are returned in a consistent envelope:

    {
        "error": {
            "code": "UPPER_SNAKE_CASE",
            "message": "Human-readable message",
            "details": [...],       # optional, for validation errors
            "request_id": "uuid"    # if request middleware active
        }
    }
"""

import logging
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Error code registry (mirrors contracts/error-response.yaml)
# ---------------------------------------------------------------------------

ERROR_CODES: dict[str, dict[str, Any]] = {
    # Auth errors
    "AUTH_INVALID_CREDENTIALS": {"http_status": 401, "message": "Invalid email or password"},
    "AUTH_TOKEN_EXPIRED": {"http_status": 401, "message": "Authentication token has expired"},
    "AUTH_TOKEN_INVALID": {"http_status": 401, "message": "Invalid authentication token"},
    "AUTH_EMAIL_TAKEN": {"http_status": 409, "message": "Email already registered"},
    "AUTH_EMAIL_NOT_VERIFIED": {"http_status": 403, "message": "Email address not verified"},
    "AUTH_FORBIDDEN": {"http_status": 403, "message": "You do not have permission to perform this action"},
    "AUTH_OAUTH_ONLY": {"http_status": 400, "message": "Cannot change password for OAuth-only accounts"},
    # Validation
    "VALIDATION_ERROR": {"http_status": 422, "message": "Request validation failed"},
    "BAD_REQUEST": {"http_status": 400, "message": "Malformed request"},
    # Resource
    "NOT_FOUND": {"http_status": 404, "message": "Resource not found"},
    "CONFLICT": {"http_status": 409, "message": "Resource conflict"},
    # Rate limiting
    "RATE_LIMITED": {"http_status": 429, "message": "Too many requests"},
    # Server
    "INTERNAL_ERROR": {"http_status": 500, "message": "An unexpected error occurred"},
}

# Reverse lookup: map (http_status, detail_substring) → error code
# Used to wrap legacy HTTPExceptions that haven't been converted yet.
_STATUS_TO_DEFAULT_CODE: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "AUTH_INVALID_CREDENTIALS",
    403: "AUTH_FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
}


# ---------------------------------------------------------------------------
# Custom exception class
# ---------------------------------------------------------------------------

class APIError(HTTPException):
    """Typed API error that carries a machine-readable error code.

    Usage:
        raise APIError("AUTH_EMAIL_TAKEN")
        raise APIError("NOT_FOUND", message="Game save not found")
        raise APIError("BAD_REQUEST", message="Room is full")
    """

    def __init__(
        self,
        code: str,
        message: str | None = None,
        details: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
    ):
        if code not in ERROR_CODES:
            logger.warning("Unknown error code %r — falling back to INTERNAL_ERROR", code)
            code = "INTERNAL_ERROR"

        entry = ERROR_CODES[code]
        self.error_code = code
        self.error_message = message or entry["message"]
        self.error_details = details
        super().__init__(
            status_code=entry["http_status"],
            detail=self.error_message,
            headers=headers,
        )


# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns a unique request_id to every request via request.state."""

    async def dispatch(self, request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_request_id(request: Request) -> str | None:
    """Safely get request_id from request state."""
    return getattr(request.state, "request_id", None)


def _map_status_to_code(status_code: int, detail: str | None = None) -> str:
    """Map an HTTP status code to the best-matching error code.

    Checks detail string for known patterns before falling back to status default.
    """
    if detail:
        detail_lower = detail.lower()
        # Auth-specific mappings based on detail text
        if status_code == 401:
            if "expired" in detail_lower:
                return "AUTH_TOKEN_EXPIRED"
            if "invalid" in detail_lower and "token" in detail_lower:
                return "AUTH_TOKEN_INVALID"
            return "AUTH_INVALID_CREDENTIALS"
        if status_code == 409 and "email" in detail_lower:
            return "AUTH_EMAIL_TAKEN"
        if status_code == 403 and "verified" in detail_lower:
            return "AUTH_EMAIL_NOT_VERIFIED"
        if status_code == 400 and "oauth" in detail_lower:
            return "AUTH_OAUTH_ONLY"
    return _STATUS_TO_DEFAULT_CODE.get(status_code, "INTERNAL_ERROR")


def _build_error_body(
    code: str,
    message: str,
    request_id: str | None = None,
    details: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the standard error response envelope."""
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    if request_id:
        error["request_id"] = request_id
    return {"error": error}


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

async def _handle_api_error(request: Request, exc: APIError) -> JSONResponse:
    """Handle our typed APIError exceptions."""
    request_id = _get_request_id(request)
    logger.warning(
        "APIError %s: %s (request_id=%s)",
        exc.error_code, exc.error_message, request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_body(
            code=exc.error_code,
            message=exc.error_message,
            request_id=request_id,
            details=exc.error_details,
        ),
        headers=exc.headers,
    )


async def _handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Wrap legacy FastAPI HTTPExceptions in the standard envelope."""
    request_id = _get_request_id(request)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    code = _map_status_to_code(exc.status_code, detail)
    logger.warning(
        "HTTPException %d → %s: %s (request_id=%s)",
        exc.status_code, code, detail, request_id,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=_build_error_body(
            code=code,
            message=detail,
            request_id=request_id,
        ),
    )


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Wrap Pydantic/FastAPI validation errors in the standard envelope."""
    request_id = _get_request_id(request)
    details = [
        {
            "field": ".".join(str(loc) for loc in e["loc"]),
            "message": e["msg"],
            "type": e["type"],
        }
        for e in exc.errors()
    ]
    logger.info(
        "Validation error: %d field(s) (request_id=%s)",
        len(details), request_id,
    )
    return JSONResponse(
        status_code=422,
        content=_build_error_body(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            request_id=request_id,
            details=details,
        ),
    )


async def _handle_unhandled(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — never expose internals."""
    request_id = _get_request_id(request)
    logger.exception(
        "Unhandled exception (request_id=%s): %s", request_id, exc,
    )
    return JSONResponse(
        status_code=500,
        content=_build_error_body(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
            request_id=request_id,
        ),
    )


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------

def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers and the request-ID middleware on the app.

    Call this once in main.py after creating the FastAPI instance.
    """
    app.add_middleware(RequestIDMiddleware)
    # APIError must be registered before HTTPException (it's a subclass)
    app.add_exception_handler(APIError, _handle_api_error)
    app.add_exception_handler(HTTPException, _handle_http_exception)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unhandled)
