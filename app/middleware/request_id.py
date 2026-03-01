"""Middleware that assigns a request ID to every request and logs request/response."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import generate_request_id, request_id_ctx

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects X-Request-ID into every request and logs start/end with timing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Use client-provided ID or generate one
        req_id = request.headers.get("X-Request-ID") or generate_request_id()
        token = request_id_ctx.set(req_id)

        method = request.method
        path = request.url.path
        logger.info("Request started: %s %s", method, path)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - start
            logger.exception("Request failed: %s %s (%.3fs)", method, path, duration)
            raise
        else:
            duration = time.perf_counter() - start
            logger.info("Request complete: %s %s → %d (%.3fs)", method, path, response.status_code, duration)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)
