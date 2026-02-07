# =============================================================================
# Room/Matchmaking Tests
# =============================================================================
# Tests for room creation, joining, and multiplayer features.
#
# Run just these tests:
#   pytest tests/test_rooms.py -v
# =============================================================================

import pytest
from tests.conftest import auth_headers


class TestRoomCreation:
    """Tests for creating rooms."""
    
    @pytest.mark.unit
    async def test_create_room(self, client, test_user, auth_token):
        """User can create a room and gets a join code."""
        response = await client.post(
            "/rooms",
            json={
                "game_id": "battle-game",
                "max_players": 2,
            },
            headers=auth_headers(auth_token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert len(data["code"]) == 6  # Default code length
        assert data["game_id"] == "battle-game"
        assert data["max_players"] == 2
        assert data["status"] == "waiting"
        assert str(test_user.id) in [str(pid) for pid in data["player_ids"]]
    
    @pytest.mark.unit
    async def test_create_room_with_data(self, client, test_user, auth_token):
        """Room can include custom game data."""
        response = await client.post(
            "/rooms",
            json={
                "game_id": "custom-game",
                "max_players": 4,
                "room_data": {
                    "map": "forest",
                    "difficulty": "hard",
                },
            },
            headers=auth_headers(auth_token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["room_data"]["map"] == "forest"
        assert data["room_data"]["difficulty"] == "hard"


class TestRoomJoining:
    """Tests for joining rooms."""
    
    @pytest.mark.unit
    async def test_join_room_by_code(
        self, client, test_user, test_user_2, auth_token, auth_token_2
    ):
        """Second user can join room using the code."""
        # User 1 creates room
        create_response = await client.post(
            "/rooms",
            json={"game_id": "battle-game", "max_players": 2},
            headers=auth_headers(auth_token),
        )
        room_code = create_response.json()["code"]
        
        # User 2 joins
        join_response = await client.post(
            "/rooms/join",
            json={"code": room_code},
            headers=auth_headers(auth_token_2),
        )
        
        assert join_response.status_code == 200
        data = join_response.json()
        assert len(data["player_ids"]) == 2
        assert str(test_user.id) in [str(pid) for pid in data["player_ids"]]
        assert str(test_user_2.id) in [str(pid) for pid in data["player_ids"]]
    
    @pytest.mark.unit
    async def test_join_room_case_insensitive(
        self, client, test_user, test_user_2, auth_token, auth_token_2
    ):
        """Room codes work regardless of case."""
        # Create room
        create_response = await client.post(
            "/rooms",
            json={"game_id": "game", "max_players": 2},
            headers=auth_headers(auth_token),
        )
        room_code = create_response.json()["code"]
        
        # Join with lowercase
        join_response = await client.post(
            "/rooms/join",
            json={"code": room_code.lower()},
            headers=auth_headers(auth_token_2),
        )
        
        assert join_response.status_code == 200
    
    @pytest.mark.unit
    async def test_join_invalid_code(self, client, test_user, auth_token):
        """Joining with invalid code returns 404."""
        response = await client.post(
            "/rooms/join",
            json={"code": "INVALID"},
            headers=auth_headers(auth_token),
        )
        
        assert response.status_code == 404
    
    @pytest.mark.unit
    async def test_join_full_room(
        self, client, test_user, test_user_2, auth_token, auth_token_2
    ):
        """Cannot join a room that's already full."""
        # Create room with max 1 player (just the host)
        create_response = await client.post(
            "/rooms",
            json={"game_id": "solo-game", "max_players": 1},
            headers=auth_headers(auth_token),
        )
        room_code = create_response.json()["code"]
        
        # User 2 tries to join
        join_response = await client.post(
            "/rooms/join",
            json={"code": room_code},
            headers=auth_headers(auth_token_2),
        )
        
        assert join_response.status_code == 400
        assert "full" in join_response.json()["detail"].lower()
    
    @pytest.mark.unit
    async def test_rejoin_room(self, client, test_user, auth_token):
        """User can rejoin a room they're already in."""
        # Create and get code
        create_response = await client.post(
            "/rooms",
            json={"game_id": "game", "max_players": 2},
            headers=auth_headers(auth_token),
        )
        room_code = create_response.json()["code"]
        
        # Try to join again (should succeed, not duplicate)
        join_response = await client.post(
            "/rooms/join",
            json={"code": room_code},
            headers=auth_headers(auth_token),
        )
        
        assert join_response.status_code == 200
        assert len(join_response.json()["player_ids"]) == 1  # Still just 1 player


class TestRoomStatus:
    """Tests for room status and game flow."""
    
    @pytest.mark.unit
    async def test_get_room_by_code(self, client, test_user, auth_token):
        """Can fetch room details by code."""
        # Create room
        create_response = await client.post(
            "/rooms",
            json={"game_id": "game", "max_players": 2},
            headers=auth_headers(auth_token),
        )
        room_code = create_response.json()["code"]
        
        # Get room
        response = await client.get(
            f"/rooms/{room_code}",
            headers=auth_headers(auth_token),
        )
        
        assert response.status_code == 200
        assert response.json()["code"] == room_code
    
    @pytest.mark.unit
    async def test_start_game_as_host(
        self, client, test_user, test_user_2, auth_token, auth_token_2
    ):
        """Host can start the game."""
        # Create and join
        create_response = await client.post(
            "/rooms",
            json={"game_id": "game", "max_players": 2},
            headers=auth_headers(auth_token),
        )
        room_code = create_response.json()["code"]
        
        await client.post(
            "/rooms/join",
            json={"code": room_code},
            headers=auth_headers(auth_token_2),
        )
        
        # Host starts game
        start_response = await client.post(
            f"/rooms/{room_code}/start",
            headers=auth_headers(auth_token),
        )
        
        assert start_response.status_code == 200
        
        # Verify status changed
        room_response = await client.get(
            f"/rooms/{room_code}",
            headers=auth_headers(auth_token),
        )
        assert room_response.json()["status"] == "playing"
    
    @pytest.mark.unit
    async def test_non_host_cannot_start(
        self, client, test_user, test_user_2, auth_token, auth_token_2
    ):
        """Non-host cannot start the game."""
        # User 1 creates room
        create_response = await client.post(
            "/rooms",
            json={"game_id": "game", "max_players": 2},
            headers=auth_headers(auth_token),
        )
        room_code = create_response.json()["code"]
        
        # User 2 joins
        await client.post(
            "/rooms/join",
            json={"code": room_code},
            headers=auth_headers(auth_token_2),
        )
        
        # User 2 tries to start (should fail)
        start_response = await client.post(
            f"/rooms/{room_code}/start",
            headers=auth_headers(auth_token_2),  # Not the host
        )
        
        assert start_response.status_code == 403
        assert "host" in start_response.json()["detail"].lower()
