import pytest
from httpx import AsyncClient
from app.main import app
from app.models.user import User
from tests.conftest import TestUser


class TestPinderAPI:
    """Test suite for Pinder dating game API endpoints"""

    async def test_upload_profile_requires_auth(self, client: AsyncClient):
        """Test that profile upload requires authentication"""
        profile_data = {
            "display_name": "TestPenis",
            "age": 25,
            "personality_prompt": "A charming test penis",
            "visual_data": {
                "skin_color": "#F4C2A1",
                "size": 5.5,
                "shape": "standard",
                "has_hat": False,
                "has_glasses": False,
                "has_accessories": False
            },
            "traits": {
                "confidence": 0.7,
                "creativity": 0.6,
                "intelligence": 0.8,
                "humor": 0.9,
                "romance": 0.5,
                "adventure": 0.4,
                "empathy": 0.7
            },
            "interests": ["gaming", "art"],
            "attractiveness_rating": 75
        }
        
        response = await client.post("/api/v1/pinder/profiles", json=profile_data)
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"]

    async def test_upload_profile_success(self, client: AsyncClient, test_user: TestUser):
        """Test successful penis profile upload"""
        profile_data = {
            "display_name": "SexyPenis",
            "age": 28,
            "personality_prompt": "A confident, humorous penis with a love for adventure",
            "visual_data": {
                "skin_color": "#F4C2A1",
                "size": 6.2,
                "shape": "standard",
                "has_hat": True,
                "has_glasses": False,
                "has_accessories": True,
                "hat_type": "fedora",
                "accessory_types": ["bow_tie"]
            },
            "traits": {
                "confidence": 0.8,
                "creativity": 0.7,
                "intelligence": 0.6,
                "humor": 0.9,
                "romance": 0.7,
                "adventure": 0.8,
                "empathy": 0.6
            },
            "interests": ["gaming", "music", "travel"],
            "attractiveness_rating": 85
        }
        
        headers = {"Authorization": f"Bearer {test_user.token}"}
        response = await client.post("/api/v1/pinder/profiles", json=profile_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "profile_id" in data
        assert data["message"] == "Profile uploaded successfully"

    async def test_fetch_matches_requires_auth(self, client: AsyncClient):
        """Test that fetching matches requires authentication"""
        match_request = {
            "count": 5,
            "player_profile": {},
            "exclude_ids": []
        }
        
        response = await client.post("/api/v1/pinder/matches", json=match_request)
        assert response.status_code == 401

    async def test_fetch_matches_success(self, client: AsyncClient, test_user: TestUser):
        """Test successful match fetching"""
        match_request = {
            "count": 3,
            "player_profile": {"test": "data"},
            "exclude_ids": ["test-id-1", "test-id-2"]
        }
        
        headers = {"Authorization": f"Bearer {test_user.token}"}
        response = await client.post("/api/v1/pinder/matches", json=match_request, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "profiles" in data
        assert len(data["profiles"]) <= 3
        assert data["message"].startswith("Found")

    async def test_submit_swipe_requires_auth(self, client: AsyncClient):
        """Test that swipe submission requires authentication"""
        swipe_data = {
            "target_profile_id": "test-profile-123",
            "direction": "right",
            "timestamp": "2026-02-16T09:00:00.000Z"
        }
        
        response = await client.post("/api/v1/pinder/swipes", json=swipe_data)
        assert response.status_code == 401

    async def test_submit_swipe_left(self, client: AsyncClient, test_user: TestUser):
        """Test left swipe submission (no match expected)"""
        swipe_data = {
            "target_profile_id": "test-profile-left-123",
            "direction": "left",
            "timestamp": "2026-02-16T09:00:00.000Z"
        }
        
        headers = {"Authorization": f"Bearer {test_user.token}"}
        response = await client.post("/api/v1/pinder/swipes", json=swipe_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["is_match"] is False
        assert data["match_id"] is None
        assert data["message"] == "Swipe recorded successfully"

    async def test_submit_swipe_right(self, client: AsyncClient, test_user: TestUser):
        """Test right swipe submission (potential match)"""
        swipe_data = {
            "target_profile_id": "test-profile-right-456",
            "direction": "right",
            "timestamp": "2026-02-16T09:00:00.000Z"
        }
        
        headers = {"Authorization": f"Bearer {test_user.token}"}
        response = await client.post("/api/v1/pinder/swipes", json=swipe_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Match outcome is probabilistic, just verify structure
        assert "is_match" in data
        assert "compatibility" in data
        if data["is_match"]:
            assert data["match_id"] is not None
            assert data["compatibility"] > 0

    async def test_get_chat_history_requires_auth(self, client: AsyncClient):
        """Test that chat history requires authentication"""
        response = await client.get("/api/v1/pinder/chats/test-match-123")
        assert response.status_code == 401

    async def test_get_chat_history_nonexistent_match(self, client: AsyncClient, test_user: TestUser):
        """Test chat history for non-existent match"""
        headers = {"Authorization": f"Bearer {test_user.token}"}
        response = await client.get("/api/v1/pinder/chats/nonexistent-match", headers=headers)
        
        assert response.status_code == 404
        assert "Match not found" in response.json()["detail"]

    async def test_send_message_requires_auth(self, client: AsyncClient):
        """Test that sending messages requires authentication"""
        message_data = {
            "match_id": "test-match-123",
            "message": "Hello there!",
            "timestamp": "2026-02-16T09:00:00.000Z"
        }
        
        response = await client.post("/api/v1/pinder/chats/send", json=message_data)
        assert response.status_code == 401

    async def test_send_message_nonexistent_match(self, client: AsyncClient, test_user: TestUser):
        """Test sending message to non-existent match"""
        message_data = {
            "match_id": "nonexistent-match",
            "message": "Hello there!",
            "timestamp": "2026-02-16T09:00:00.000Z"
        }
        
        headers = {"Authorization": f"Bearer {test_user.token}"}
        response = await client.post("/api/v1/pinder/chats/send", json=message_data, headers=headers)
        
        assert response.status_code == 404
        assert "Match not found" in response.json()["detail"]

    async def test_get_stats_requires_auth(self, client: AsyncClient):
        """Test that stats endpoint requires authentication"""
        response = await client.get("/api/v1/pinder/stats")
        assert response.status_code == 401

    async def test_get_stats_success(self, client: AsyncClient, test_user: TestUser):
        """Test successful stats retrieval"""
        headers = {"Authorization": f"Bearer {test_user.token}"}
        response = await client.get("/api/v1/pinder/stats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stats" in data
        
        stats = data["stats"]
        assert "total_swipes" in stats
        assert "total_matches" in stats
        assert "swipe_right_count" in stats
        assert "swipe_left_count" in stats
        assert "match_rate" in stats
        assert "average_compatibility" in stats

    async def test_profile_data_validation(self, client: AsyncClient, test_user: TestUser):
        """Test profile upload with invalid data"""
        # Missing required fields
        invalid_profile = {
            "display_name": "TestPenis"
            # Missing age, personality_prompt, visual_data, traits
        }
        
        headers = {"Authorization": f"Bearer {test_user.token}"}
        response = await client.post("/api/v1/pinder/profiles", json=invalid_profile, headers=headers)
        
        assert response.status_code == 422  # Validation error

    async def test_swipe_data_validation(self, client: AsyncClient, test_user: TestUser):
        """Test swipe with invalid direction"""
        invalid_swipe = {
            "target_profile_id": "test-123",
            "direction": "up",  # Invalid direction
            "timestamp": "2026-02-16T09:00:00.000Z"
        }
        
        headers = {"Authorization": f"Bearer {test_user.token}"}
        response = await client.post("/api/v1/pinder/swipes", json=invalid_swipe, headers=headers)
        
        # Should still work since backend doesn't validate direction enum
        assert response.status_code == 200

    async def test_match_request_validation(self, client: AsyncClient, test_user: TestUser):
        """Test match request with invalid count"""
        invalid_match_request = {
            "count": -5,  # Negative count
            "player_profile": {},
            "exclude_ids": []
        }
        
        headers = {"Authorization": f"Bearer {test_user.token}"}
        response = await client.post("/api/v1/pinder/matches", json=invalid_match_request, headers=headers)
        
        # Backend should handle this gracefully
        assert response.status_code == 200
        data = response.json()
        assert len(data["profiles"]) == 0  # Should return empty list


class TestPinderIntegration:
    """Integration tests for complete Pinder workflows"""

    async def test_complete_dating_flow(self, client: AsyncClient, test_user: TestUser):
        """Test complete flow: profile → matches → swipe → chat"""
        headers = {"Authorization": f"Bearer {test_user.token}"}
        
        # 1. Upload profile
        profile_data = {
            "display_name": "FlowTestPenis",
            "age": 30,
            "personality_prompt": "A penis ready for love",
            "visual_data": {
                "skin_color": "#F4C2A1",
                "size": 5.8,
                "shape": "standard",
                "has_hat": False,
                "has_glasses": True,
                "has_accessories": False,
                "glasses_type": "aviator"
            },
            "traits": {
                "confidence": 0.7,
                "creativity": 0.5,
                "intelligence": 0.8,
                "humor": 0.6,
                "romance": 0.9,
                "adventure": 0.4,
                "empathy": 0.8
            },
            "interests": ["romance", "philosophy"],
            "attractiveness_rating": 78
        }
        
        profile_response = await client.post("/api/v1/pinder/profiles", json=profile_data, headers=headers)
        assert profile_response.status_code == 200
        
        # 2. Fetch matches
        match_request = {"count": 5, "player_profile": {}, "exclude_ids": []}
        match_response = await client.post("/api/v1/pinder/matches", json=match_request, headers=headers)
        assert match_response.status_code == 200
        
        matches = match_response.json()["profiles"]
        assert len(matches) > 0
        
        # 3. Swipe right on first match
        target_id = matches[0]["profile_id"]
        swipe_data = {
            "target_profile_id": target_id,
            "direction": "right",
            "timestamp": "2026-02-16T09:05:00.000Z"
        }
        
        swipe_response = await client.post("/api/v1/pinder/swipes", json=swipe_data, headers=headers)
        assert swipe_response.status_code == 200
        
        # 4. Get stats to verify swipe was recorded
        stats_response = await client.get("/api/v1/pinder/stats", headers=headers)
        assert stats_response.status_code == 200
        
        stats = stats_response.json()["stats"]
        assert stats["total_swipes"] >= 1
        assert stats["swipe_right_count"] >= 1

    async def test_performance_multiple_requests(self, client: AsyncClient, test_user: TestUser):
        """Test API performance with multiple concurrent requests"""
        import asyncio
        
        headers = {"Authorization": f"Bearer {test_user.token}"}
        
        # Create multiple match requests simultaneously
        async def fetch_matches():
            match_request = {"count": 2, "player_profile": {}, "exclude_ids": []}
            return await client.post("/api/v1/pinder/matches", json=match_request, headers=headers)
        
        # Run 5 concurrent requests
        tasks = [fetch_matches() for _ in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["success"] is True