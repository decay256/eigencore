# =============================================================================
# Auth Tests
# =============================================================================
# Tests for user registration, login, and authentication.
#
# Run just these tests:
#   pytest tests/test_auth.py -v
# =============================================================================

import pytest
from tests.conftest import auth_headers


class TestRegistration:
    """Tests for user registration."""
    
    @pytest.mark.unit
    async def test_register_success(self, client):
        """New user can register with email and password."""
        response = await client.post("/auth/register", json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "display_name": "New User",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["display_name"] == "New User"
    
    @pytest.mark.unit
    async def test_register_duplicate_email(self, client, test_user):
        """Cannot register with an email that's already in use."""
        response = await client.post("/auth/register", json={
            "email": test_user.email,  # Already exists
            "password": "securepassword123",
            "display_name": "Another User",
        })
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    @pytest.mark.unit
    async def test_register_invalid_email(self, client):
        """Registration fails with invalid email format."""
        response = await client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "securepassword123",
            "display_name": "Bad Email User",
        })
        
        assert response.status_code == 422  # Validation error


class TestLogin:
    """Tests for user login."""
    
    @pytest.mark.unit
    async def test_login_success(self, client, test_user):
        """User can login with correct credentials."""
        response = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "testpassword123",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"
    
    @pytest.mark.unit
    async def test_login_wrong_password(self, client, test_user):
        """Login fails with incorrect password."""
        response = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()
    
    @pytest.mark.unit
    async def test_login_nonexistent_user(self, client):
        """Login fails for user that doesn't exist."""
        response = await client.post("/auth/login", json={
            "email": "nobody@example.com",
            "password": "anypassword",
        })
        
        assert response.status_code == 401


class TestAuthenticatedEndpoints:
    """Tests for endpoints that require authentication."""
    
    @pytest.mark.unit
    async def test_get_me_authenticated(self, client, test_user, auth_token):
        """Authenticated user can access /auth/me."""
        response = await client.get(
            "/auth/me", 
            headers=auth_headers(auth_token)
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["display_name"] == test_user.display_name
    
    @pytest.mark.unit
    async def test_get_me_no_token(self, client):
        """Unauthenticated request to /auth/me fails."""
        response = await client.get("/auth/me")
        
        assert response.status_code == 401  # No auth header = Unauthorized
    
    @pytest.mark.unit
    async def test_get_me_invalid_token(self, client):
        """Request with invalid token fails."""
        response = await client.get(
            "/auth/me",
            headers=auth_headers("invalid-token-here")
        )
        
        assert response.status_code == 401
