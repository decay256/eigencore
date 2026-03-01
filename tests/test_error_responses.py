"""Tests for standardized error response format (Issue #14).

Verifies that all error responses conform to the error-response contract:
- Standard envelope: {"error": {"code": "...", "message": "...", ...}}
- Request ID present in error responses
- Validation errors include field-level details
- Legacy HTTPExceptions are wrapped correctly
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.errors import (
    APIError,
    ERROR_CODES,
    register_error_handlers,
    _map_status_to_code,
    _build_error_body,
)


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------

class TestMapStatusToCode:
    def test_401_default(self):
        assert _map_status_to_code(401) == "AUTH_INVALID_CREDENTIALS"

    def test_401_expired(self):
        assert _map_status_to_code(401, "Token has expired") == "AUTH_TOKEN_EXPIRED"

    def test_401_invalid_token(self):
        assert _map_status_to_code(401, "Invalid token provided") == "AUTH_TOKEN_INVALID"

    def test_404(self):
        assert _map_status_to_code(404) == "NOT_FOUND"

    def test_409_email(self):
        assert _map_status_to_code(409, "Email already registered") == "AUTH_EMAIL_TAKEN"

    def test_unknown_status(self):
        assert _map_status_to_code(418) == "INTERNAL_ERROR"


class TestBuildErrorBody:
    def test_minimal(self):
        body = _build_error_body("NOT_FOUND", "Resource not found")
        assert body == {"error": {"code": "NOT_FOUND", "message": "Resource not found"}}

    def test_with_request_id(self):
        body = _build_error_body("NOT_FOUND", "gone", request_id="abc-123")
        assert body["error"]["request_id"] == "abc-123"

    def test_with_details(self):
        details = [{"field": "body.email", "message": "invalid", "type": "value_error"}]
        body = _build_error_body("VALIDATION_ERROR", "fail", details=details)
        assert body["error"]["details"] == details

    def test_no_details_key_when_none(self):
        body = _build_error_body("NOT_FOUND", "nope")
        assert "details" not in body["error"]


class TestAPIError:
    def test_known_code(self):
        err = APIError("AUTH_EMAIL_TAKEN")
        assert err.error_code == "AUTH_EMAIL_TAKEN"
        assert err.status_code == 409
        assert err.error_message == "Email already registered"

    def test_custom_message(self):
        err = APIError("NOT_FOUND", message="Game save not found")
        assert err.error_message == "Game save not found"
        assert err.status_code == 404

    def test_unknown_code_falls_back(self):
        err = APIError("TOTALLY_BOGUS")
        assert err.error_code == "INTERNAL_ERROR"
        assert err.status_code == 500


# ---------------------------------------------------------------------------
# Integration tests with a test FastAPI app
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app():
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/api-error")
    async def raise_api_error():
        raise APIError("AUTH_EMAIL_TAKEN")

    @app.get("/http-error")
    async def raise_http_error():
        raise HTTPException(status_code=404, detail="Save state not found")

    @app.get("/unhandled")
    async def raise_unhandled():
        raise RuntimeError("kaboom")

    from pydantic import BaseModel

    class Item(BaseModel):
        name: str
        count: int

    @app.post("/validate")
    async def validate_item(item: Item):
        return {"ok": True}

    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app, raise_server_exceptions=False)


class TestErrorHandlerIntegration:
    def test_api_error_envelope(self, client):
        resp = client.get("/api-error")
        assert resp.status_code == 409
        body = resp.json()
        assert "error" in body
        assert body["error"]["code"] == "AUTH_EMAIL_TAKEN"
        assert body["error"]["message"] == "Email already registered"
        assert "request_id" in body["error"]

    def test_http_exception_wrapped(self, client):
        resp = client.get("/http-error")
        assert resp.status_code == 404
        body = resp.json()
        assert body["error"]["code"] == "NOT_FOUND"
        assert "request_id" in body["error"]

    def test_validation_error(self, client):
        resp = client.post("/validate", json={"name": 123})
        assert resp.status_code == 422
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "details" in body["error"]
        assert len(body["error"]["details"]) > 0
        assert "field" in body["error"]["details"][0]

    def test_unhandled_exception(self, client):
        resp = client.get("/unhandled")
        assert resp.status_code == 500
        body = resp.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        # Must not leak internals
        assert "kaboom" not in body["error"]["message"]

    def test_request_id_header(self, client):
        resp = client.get("/api-error")
        assert "x-request-id" in resp.headers

    def test_request_id_in_success_response(self, client):
        """Request ID header should be on all responses, not just errors."""
        resp = client.post("/validate", json={"name": "test", "count": 1})
        assert resp.status_code == 200
        assert "x-request-id" in resp.headers


class TestErrorCodeRegistry:
    def test_all_codes_have_required_fields(self):
        for code, entry in ERROR_CODES.items():
            assert "http_status" in entry, f"{code} missing http_status"
            assert "message" in entry, f"{code} missing message"
            assert isinstance(entry["http_status"], int)
            assert 400 <= entry["http_status"] <= 599, f"{code} has non-error status {entry['http_status']}"
