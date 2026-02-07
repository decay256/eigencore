from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Any


class GameStateCreate(BaseModel):
    game_id: str
    slot_name: str = "default"
    state_data: dict[str, Any]
    version: str | None = None


class GameStateUpdate(BaseModel):
    state_data: dict[str, Any]
    version: str | None = None


class GameStateResponse(BaseModel):
    id: UUID
    user_id: UUID
    game_id: str
    slot_name: str
    state_data: dict[str, Any]
    version: str | None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
