from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
from uuid import UUID

from app.db.database import get_db
from app.models.user import User
from app.models.room import Room, generate_room_code
from app.schemas.room import RoomCreate, RoomJoin, RoomResponse
from app.api.deps import get_current_user
from app.core.security import decode_token
from app.core.connection_manager import manager

router = APIRouter(prefix="/rooms", tags=["rooms"])


def parse_player_ids(player_ids_str: str | None) -> list[UUID]:
    if not player_ids_str:
        return []
    return [UUID(pid) for pid in json.loads(player_ids_str)]


def serialize_player_ids(player_ids: list[UUID]) -> str:
    return json.dumps([str(pid) for pid in player_ids])


@router.post("", response_model=RoomResponse)
async def create_room(
    room_data: RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new room and get a join code."""
    # Generate unique room code
    for _ in range(10):
        code = generate_room_code()
        result = await db.execute(select(Room).where(Room.code == code))
        if not result.scalar_one_or_none():
            break
    else:
        raise HTTPException(status_code=500, detail="Failed to generate unique room code")
    
    room = Room(
        code=code,
        game_id=room_data.game_id,
        host_user_id=current_user.id,
        max_players=room_data.max_players,
        is_private=room_data.is_private,
        player_ids=serialize_player_ids([current_user.id]),
        room_data=json.dumps(room_data.room_data) if room_data.room_data else None,
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    
    return RoomResponse(
        id=room.id,
        code=room.code,
        game_id=room.game_id,
        host_user_id=room.host_user_id,
        max_players=room.max_players,
        is_private=room.is_private,
        status=room.status,
        player_ids=parse_player_ids(room.player_ids),
        room_data=json.loads(room.room_data) if room.room_data else None,
        created_at=room.created_at,
    )


@router.post("/join", response_model=RoomResponse)
async def join_room(
    join_data: RoomJoin,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join a room by code."""
    result = await db.execute(select(Room).where(Room.code == join_data.code.upper()))
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.status != "waiting":
        raise HTTPException(status_code=400, detail="Room is not accepting players")
    
    player_ids = parse_player_ids(room.player_ids)
    
    if current_user.id in player_ids:
        # Already in room, just return it
        pass
    elif len(player_ids) >= room.max_players:
        raise HTTPException(status_code=400, detail="Room is full")
    else:
        player_ids.append(current_user.id)
        room.player_ids = serialize_player_ids(player_ids)
        await db.commit()
        await db.refresh(room)
    
    return RoomResponse(
        id=room.id,
        code=room.code,
        game_id=room.game_id,
        host_user_id=room.host_user_id,
        max_players=room.max_players,
        is_private=room.is_private,
        status=room.status,
        player_ids=parse_player_ids(room.player_ids),
        room_data=json.loads(room.room_data) if room.room_data else None,
        created_at=room.created_at,
    )


@router.get("/{code}", response_model=RoomResponse)
async def get_room(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get room details."""
    result = await db.execute(select(Room).where(Room.code == code.upper()))
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return RoomResponse(
        id=room.id,
        code=room.code,
        game_id=room.game_id,
        host_user_id=room.host_user_id,
        max_players=room.max_players,
        is_private=room.is_private,
        status=room.status,
        player_ids=parse_player_ids(room.player_ids),
        room_data=json.loads(room.room_data) if room.room_data else None,
        created_at=room.created_at,
    )


@router.post("/{code}/start")
async def start_room(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start the game (host only)."""
    result = await db.execute(select(Room).where(Room.code == code.upper()))
    room = result.scalar_one_or_none()
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if room.host_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the host can start the game")
    
    room.status = "playing"
    await db.commit()
    
    # Notify connected clients
    await manager.broadcast(code, {"type": "game_started"})
    
    return {"ok": True}


@router.websocket("/{code}/ws")
async def room_websocket(
    websocket: WebSocket,
    code: str,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket for real-time room communication."""
    # Validate token
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    
    user_id = UUID(payload["sub"])
    
    # Check room exists and user is a member
    result = await db.execute(select(Room).where(Room.code == code.upper()))
    room = result.scalar_one_or_none()
    
    if not room:
        await websocket.close(code=4004)
        return
    
    player_ids = parse_player_ids(room.player_ids)
    if user_id not in player_ids:
        await websocket.close(code=4003)
        return
    
    await websocket.accept()
    
    # Add to room connections
    manager.connect(code, websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            # Broadcast to all other clients in the room
            await manager.broadcast_except(
                code,
                {"type": "message", "from": str(user_id), "data": data},
                exclude=websocket,
            )
    except WebSocketDisconnect:
        manager.disconnect(code, websocket)
