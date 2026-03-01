"""Tests for standardized error response format (Issue #14).

Verifies that all error responses follow the structure:
{
    "error": {
        "code": "<ERROR_CODE>",
        "message": "<human-readable>",
        "details": { ... }  // optional
    }
}
"""

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def assert_error_shape(data: dict, expected_code: str):
    """Assert the response matches the standard error envelope."""
    assert "error" in data, f"Missing 'error' key in response: {data}"
    err = data["error"]
    assert "code" in err, f"Missing 'code' in error: {err}"
    assert "message" in err, f"Missing 'message' in error: {err}"
    assert err["code"] == expected_code, f"Expected code {expected_code}, got {err['code']}"
    assert isinstance(err["message"], str)
    # Must NOT have old-style 'detail' key at top level
    assert "detail" not in data, f"Old-style 'detail' key found: {data}"


async def test_404_returns_standard_format(client):
    """Unknown routes return standardized NOT_FOUND error."""
    resp = await client.get("/api/v1/nonexistent")
    assert resp.status_code == 404
    assert_error_shape(resp.json(), "NOT_FOUND")


async def test_401_no_token(client):
    """Accessing protected endpoint without token returns error in standard format."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code in (401, 403)
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] in ("UNAUTHORIZED", "FORBIDDEN")


async def test_401_invalid_token(client):
    """Invalid bearer token returns standardized UNAUTHORIZED."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert resp.status_code == 401
    assert_error_shape(resp.json(), "UNAUTHORIZED")


async def test_validation_error_returns_standard_format(client):
    """Invalid data returns VALIDATION_ERROR with details."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email"},  # missing required fields
    )
    assert resp.status_code == 422
    data = resp.json()
    assert_error_shape(data, "VALIDATION_ERROR")
    assert "details" in data["error"]
    assert "validation_errors" in data["error"]["details"]


async def test_error_envelope_no_detail_key(client):
    """Ensure old-style {'detail': '...'} format is NOT returned."""
    resp = await client.get("/api/v1/nonexistent")
    data = resp.json()
    assert "detail" not in data


async def test_method_not_allowed(client):
    """Wrong HTTP method returns standard error format."""
    resp = await client.delete("/api/v1/auth/login")
    assert resp.status_code == 405
    data = resp.json()
    assert "error" in data


async def test_error_response_schema_import():
    """Verify ErrorResponse schema is importable and well-formed."""
    from app.core.errors import ErrorResponse, ErrorCode
    resp = ErrorResponse(error={"code": ErrorCode.NOT_FOUND, "message": "test"})
    assert resp.error.code == "NOT_FOUND"
    assert resp.error.message == "test"
    assert resp.error.details is None
