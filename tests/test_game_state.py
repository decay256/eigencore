# =============================================================================
# Game State Tests
# =============================================================================
# Tests for saving and loading game state.
#
# Run just these tests:
#   pytest tests/test_game_state.py -v
# =============================================================================

import pytest
from tests.conftest import auth_headers


class TestGameStateCRUD:
    """Tests for game state create, read, update, delete."""
    
    @pytest.mark.unit
    async def test_create_game_state(self, client, test_user, auth_token):
        """User can save game state."""
        response = await client.post(
            "/games/plant-simulator/state",
            json={
                "game_id": "plant-simulator",
                "slot_name": "save1",
                "state_data": {
                    "plants": [{"type": "rose", "growth": 0.5}],
                    "sun_position": 45.0,
                    "day": 7,
                },
                "version": "1.0.0",
            },
            headers=auth_headers(auth_token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == "plant-simulator"
        assert data["slot_name"] == "save1"
        assert data["state_data"]["day"] == 7
        assert len(data["state_data"]["plants"]) == 1
    
    @pytest.mark.unit
    async def test_get_game_state(self, client, test_user, auth_token):
        """User can load a saved game state."""
        # First, create a save
        await client.post(
            "/games/plant-simulator/state",
            json={
                "game_id": "plant-simulator",
                "slot_name": "mysave",
                "state_data": {"level": 5},
            },
            headers=auth_headers(auth_token),
        )
        
        # Then, load it
        response = await client.get(
            "/games/plant-simulator/state/mysave",
            headers=auth_headers(auth_token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["state_data"]["level"] == 5
    
    @pytest.mark.unit
    async def test_update_game_state(self, client, test_user, auth_token):
        """Saving to the same slot updates the state."""
        # Create initial save
        await client.post(
            "/games/mygame/state",
            json={
                "game_id": "mygame",
                "slot_name": "slot1",
                "state_data": {"score": 100},
            },
            headers=auth_headers(auth_token),
        )
        
        # Update the same slot
        response = await client.post(
            "/games/mygame/state",
            json={
                "game_id": "mygame",
                "slot_name": "slot1",
                "state_data": {"score": 200},  # Updated score
            },
            headers=auth_headers(auth_token),
        )
        
        assert response.status_code == 200
        assert response.json()["state_data"]["score"] == 200
        
        # Verify it was updated, not duplicated
        list_response = await client.get(
            "/games/mygame/state",
            headers=auth_headers(auth_token),
        )
        assert len(list_response.json()) == 1
    
    @pytest.mark.unit
    async def test_list_game_states(self, client, test_user, auth_token):
        """User can list all their saves for a game."""
        # Create multiple saves
        for slot in ["slot1", "slot2", "slot3"]:
            await client.post(
                "/games/mygame/state",
                json={
                    "game_id": "mygame",
                    "slot_name": slot,
                    "state_data": {"slot": slot},
                },
                headers=auth_headers(auth_token),
            )
        
        response = await client.get(
            "/games/mygame/state",
            headers=auth_headers(auth_token),
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        slot_names = {s["slot_name"] for s in data}
        assert slot_names == {"slot1", "slot2", "slot3"}
    
    @pytest.mark.unit
    async def test_delete_game_state(self, client, test_user, auth_token):
        """User can delete a save slot."""
        # Create a save
        await client.post(
            "/games/mygame/state",
            json={
                "game_id": "mygame",
                "slot_name": "todelete",
                "state_data": {"data": "test"},
            },
            headers=auth_headers(auth_token),
        )
        
        # Delete it
        response = await client.delete(
            "/games/mygame/state/todelete",
            headers=auth_headers(auth_token),
        )
        
        assert response.status_code == 200
        
        # Verify it's gone
        get_response = await client.get(
            "/games/mygame/state/todelete",
            headers=auth_headers(auth_token),
        )
        assert get_response.status_code == 404
    
    @pytest.mark.unit
    async def test_get_nonexistent_state(self, client, test_user, auth_token):
        """Getting a non-existent save returns 404."""
        response = await client.get(
            "/games/mygame/state/doesnotexist",
            headers=auth_headers(auth_token),
        )
        
        assert response.status_code == 404


class TestGameStateIsolation:
    """Tests that users can't access each other's saves."""
    
    @pytest.mark.unit
    async def test_users_cant_see_each_others_saves(
        self, client, test_user, test_user_2, auth_token, auth_token_2
    ):
        """User 1's saves are not visible to User 2."""
        # User 1 creates a save
        await client.post(
            "/games/mygame/state",
            json={
                "game_id": "mygame",
                "slot_name": "secret",
                "state_data": {"secret": "data"},
            },
            headers=auth_headers(auth_token),
        )
        
        # User 2 tries to access it
        response = await client.get(
            "/games/mygame/state/secret",
            headers=auth_headers(auth_token_2),
        )
        
        assert response.status_code == 404  # Can't see User 1's save
        
        # User 2's list should be empty
        list_response = await client.get(
            "/games/mygame/state",
            headers=auth_headers(auth_token_2),
        )
        assert len(list_response.json()) == 0
