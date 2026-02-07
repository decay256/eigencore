from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Any


class RoomCreate(BaseModel):
    game_id: str
    max_players: int = 2
    is_private: bool = False
    room_data: dict[str, Any] | None = None


class RoomJoin(BaseModel):
    code: str


class RoomResponse(BaseModel):
    id: UUID
    code: str
    game_id: str
    host_user_id: UUID
    max_players: int
    is_private: bool
    status: str
    player_ids: list[UUID] | None
    room_data: dict[str, Any] | None
    created_at: datetime
    
    class Config:
        from_attributes = True
