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
        
        assert response.status_code == 409
        assert "already registered" in response.json()["error"]["message"].lower()
    
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
        # OAuth2 password flow uses form data with 'username' field
        response = await client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "testpassword123",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "test@example.com"
    
    @pytest.mark.unit
    async def test_login_wrong_password(self, client, test_user):
        """Login fails with incorrect password."""
        response = await client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "wrongpassword",
        })
        
        assert response.status_code == 401
        assert "invalid" in response.json()["error"]["message"].lower()
    
    @pytest.mark.unit
    async def test_login_nonexistent_user(self, client):
        """Login fails for user that doesn't exist."""
        response = await client.post("/auth/login", data={
            "username": "nobody@example.com",
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


class TestProfileUpdate:
    """Tests for profile update endpoints."""
    
    @pytest.mark.unit
    async def test_update_display_name(self, client, test_user, auth_token):
        """User can update their display name."""
        response = await client.patch(
            "/auth/me",
            headers=auth_headers(auth_token),
            json={"display_name": "Updated Name"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "Updated Name"
    
    @pytest.mark.unit
    async def test_update_display_name_too_short(self, client, test_user, auth_token):
        """Display name must be at least 2 characters."""
        response = await client.patch(
            "/auth/me",
            headers=auth_headers(auth_token),
            json={"display_name": "X"}
        )
        
        assert response.status_code == 400
        assert "2 and 32" in response.json()["error"]["message"]
    
    @pytest.mark.unit
    async def test_update_avatar_url(self, client, test_user, auth_token):
        """User can set an avatar URL."""
        response = await client.patch(
            "/auth/me",
            headers=auth_headers(auth_token),
            json={"avatar_url": "https://example.com/avatar.png"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["avatar_url"] == "https://example.com/avatar.png"
    
    @pytest.mark.unit
    async def test_update_avatar_invalid_url(self, client, test_user, auth_token):
        """Avatar URL must be a valid HTTP URL."""
        response = await client.patch(
            "/auth/me",
            headers=auth_headers(auth_token),
            json={"avatar_url": "not-a-url"}
        )
        
        assert response.status_code == 400
        assert "HTTP" in response.json()["error"]["message"]


class TestPasswordChange:
    """Tests for password change endpoint."""
    
    @pytest.mark.unit
    async def test_change_password_success(self, client, test_user, auth_token):
        """User can change their password."""
        response = await client.post(
            "/auth/change-password",
            headers=auth_headers(auth_token),
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456"
            }
        )
        
        assert response.status_code == 200
        assert "successfully" in response.json()["message"].lower()
        
        # Verify old password no longer works
        login_response = await client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "testpassword123",
        })
        assert login_response.status_code == 401
        
        # Verify new password works
        login_response = await client.post("/auth/login", data={
            "username": "test@example.com",
            "password": "newpassword456",
        })
        assert login_response.status_code == 200
    
    @pytest.mark.unit
    async def test_change_password_wrong_current(self, client, test_user, auth_token):
        """Cannot change password with wrong current password."""
        response = await client.post(
            "/auth/change-password",
            headers=auth_headers(auth_token),
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456"
            }
        )
        
        assert response.status_code == 401
        assert "incorrect" in response.json()["error"]["message"].lower()
    
    @pytest.mark.unit
    async def test_change_password_too_short(self, client, test_user, auth_token):
        """New password must be at least 8 characters."""
        response = await client.post(
            "/auth/change-password",
            headers=auth_headers(auth_token),
            json={
                "current_password": "testpassword123",
                "new_password": "short"
            }
        )
        
        assert response.status_code == 400
        assert "8 characters" in response.json()["error"]["message"]


class TestAccountDeletion:
    """Tests for account deletion endpoint."""
    
    @pytest.mark.unit
    async def test_delete_account(self, client, test_user, auth_token):
        """User can delete their account."""
        response = await client.delete(
            "/auth/me",
            headers=auth_headers(auth_token)
        )
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()
        
        # Verify token no longer works
        me_response = await client.get(
            "/auth/me",
            headers=auth_headers(auth_token)
        )
        assert me_response.status_code == 401


class TestOAuthEndpoints:
    """Tests for OAuth authentication endpoints."""
    
    @pytest.mark.unit
    async def test_discord_oauth_redirect_when_configured(self, client, monkeypatch):
        """Discord OAuth redirects to Discord when configured."""
        from app.api.routes import oauth
        from app.core.config import Settings
        
        # Create mock settings and patch the module-level settings object
        mock = Settings(
            discord_client_id="test_client_id",
            discord_client_secret="test_client_secret",
            discord_redirect_uri="http://localhost:8000/api/v1/auth/discord/callback",
        )
        monkeypatch.setattr(oauth, "settings", mock)
        
        response = await client.get("/auth/discord", follow_redirects=False)
        
        assert response.status_code == 307
        assert "discord.com" in response.headers["location"]
        assert "client_id=test_client_id" in response.headers["location"]
    
    @pytest.mark.unit
    async def test_discord_oauth_not_configured(self, client, monkeypatch):
        """Discord OAuth returns 501 when not configured."""
        from app.api.routes import oauth
        from app.core.config import Settings
        
        mock = Settings(
            discord_client_id=None,
            discord_client_secret=None,
        )
        monkeypatch.setattr(oauth, "settings", mock)
        
        response = await client.get("/auth/discord")
        
        assert response.status_code == 501
        assert "not configured" in response.json()["error"]["message"].lower()
    
    @pytest.mark.unit
    async def test_google_oauth_not_configured(self, client, monkeypatch):
        """Google OAuth returns 501 when not configured."""
        from app.api.routes import oauth
        from app.core.config import Settings
        
        mock = Settings(
            google_client_id=None,
            google_client_secret=None,
        )
        monkeypatch.setattr(oauth, "settings", mock)
        
        response = await client.get("/auth/google")
        
        assert response.status_code == 501
        assert "not configured" in response.json()["error"]["message"].lower()
    
    @pytest.mark.unit
    async def test_steam_oauth_not_configured(self, client, monkeypatch):
        """Steam OAuth returns 501 when not configured."""
        from app.api.routes import oauth
        from app.core.config import Settings
        
        mock = Settings(
            steam_api_key=None,
        )
        monkeypatch.setattr(oauth, "settings", mock)
        
        response = await client.get("/auth/steam")
        
        assert response.status_code == 501
        assert "not configured" in response.json()["error"]["message"].lower()
