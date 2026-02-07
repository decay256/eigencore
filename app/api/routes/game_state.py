from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.db.database import get_db
from app.models.user import User
from app.models.game_state import GameState
from app.schemas.game_state import GameStateCreate, GameStateUpdate, GameStateResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/games", tags=["game-state"])


@router.get("/{game_id}/state", response_model=list[GameStateResponse])
async def list_game_states(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all save slots for a game."""
    result = await db.execute(
        select(GameState).where(
            GameState.user_id == current_user.id,
            GameState.game_id == game_id,
        )
    )
    states = result.scalars().all()
    
    # Parse JSON state_data
    response = []
    for state in states:
        state_dict = {
            "id": state.id,
            "user_id": state.user_id,
            "game_id": state.game_id,
            "slot_name": state.slot_name,
            "state_data": json.loads(state.state_data) if state.state_data else {},
            "version": state.version,
            "created_at": state.created_at,
            "updated_at": state.updated_at,
        }
        response.append(GameStateResponse(**state_dict))
    
    return response


@router.get("/{game_id}/state/{slot_name}", response_model=GameStateResponse)
async def get_game_state(
    game_id: str,
    slot_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific save slot."""
    result = await db.execute(
        select(GameState).where(
            GameState.user_id == current_user.id,
            GameState.game_id == game_id,
            GameState.slot_name == slot_name,
        )
    )
    state = result.scalar_one_or_none()
    
    if not state:
        raise HTTPException(status_code=404, detail="Save state not found")
    
    return GameStateResponse(
        id=state.id,
        user_id=state.user_id,
        game_id=state.game_id,
        slot_name=state.slot_name,
        state_data=json.loads(state.state_data) if state.state_data else {},
        version=state.version,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


@router.post("/{game_id}/state", response_model=GameStateResponse)
async def create_game_state(
    game_id: str,
    state_data: GameStateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update a save slot."""
    # Check if slot exists
    result = await db.execute(
        select(GameState).where(
            GameState.user_id == current_user.id,
            GameState.game_id == game_id,
            GameState.slot_name == state_data.slot_name,
        )
    )
    state = result.scalar_one_or_none()
    
    if state:
        # Update existing
        state.state_data = json.dumps(state_data.state_data)
        state.version = state_data.version
    else:
        # Create new
        state = GameState(
            user_id=current_user.id,
            game_id=game_id,
            slot_name=state_data.slot_name,
            state_data=json.dumps(state_data.state_data),
            version=state_data.version,
        )
        db.add(state)
    
    await db.commit()
    await db.refresh(state)
    
    return GameStateResponse(
        id=state.id,
        user_id=state.user_id,
        game_id=state.game_id,
        slot_name=state.slot_name,
        state_data=json.loads(state.state_data) if state.state_data else {},
        version=state.version,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


@router.delete("/{game_id}/state/{slot_name}")
async def delete_game_state(
    game_id: str,
    slot_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a save slot."""
    result = await db.execute(
        select(GameState).where(
            GameState.user_id == current_user.id,
            GameState.game_id == game_id,
            GameState.slot_name == slot_name,
        )
    )
    state = result.scalar_one_or_none()
    
    if not state:
        raise HTTPException(status_code=404, detail="Save state not found")
    
    await db.delete(state)
    await db.commit()
    
    return {"ok": True}
