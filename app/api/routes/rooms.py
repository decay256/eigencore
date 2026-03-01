from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import logging
from uuid import UUID

from app.db.database import get_db
from app.models.user import User
from app.models.room import Room, generate_room_code
from app.models.room_player import RoomPlayer
from app.schemas.room import RoomCreate, RoomJoin, RoomResponse
from app.api.deps import get_current_user
from app.core.security import decode_token
from app.core.connection_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rooms", tags=["rooms"])


def get_player_ids(room: Room) -> list[UUID]:
    """Extract player UUIDs from a room's players relationship."""
    return [rp.user_id for rp in room.players]


def build_room_response(room: Room) -> RoomResponse:
    return RoomResponse(
        id=room.id,
        code=room.code,
        game_id=room.game_id,
        host_user_id=room.host_user_id,
        max_players=room.max_players,
        is_private=room.is_private,
        status=room.status,
        player_ids=get_player_ids(room),
        room_data=json.loads(room.room_data) if room.room_data else None,
        created_at=room.created_at,
    )


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
        room_data=json.dumps(room_data.room_data) if room_data.room_data else None,
    )
    db.add(room)
    await db.flush()  # get room.id

    # Add host as first player
    db.add(RoomPlayer(room_id=room.id, user_id=current_user.id))
    await db.commit()
    await db.refresh(room)

    logger.info("Room created: code=%s, game=%s, host=%s", code, room_data.game_id, current_user.id)
    return build_room_response(room)


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

    player_ids = get_player_ids(room)

    if current_user.id in player_ids:
        pass  # Already in room
    elif len(player_ids) >= room.max_players:
        raise HTTPException(status_code=400, detail="Room is full")
    else:
        db.add(RoomPlayer(room_id=room.id, user_id=current_user.id))
        await db.commit()
        await db.refresh(room)
        logger.info("Player %s joined room %s", current_user.id, room.code)

    return build_room_response(room)


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

    return build_room_response(room)


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
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = UUID(payload["sub"])

    result = await db.execute(select(Room).where(Room.code == code.upper()))
    room = result.scalar_one_or_none()

    if not room:
        await websocket.close(code=4004)
        return

    player_ids = get_player_ids(room)
    if user_id not in player_ids:
        await websocket.close(code=4003)
        return

    await websocket.accept()
    manager.connect(code, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast_except(
                code,
                {"type": "message", "from": str(user_id), "data": data},
                exclude=websocket,
            )
    except WebSocketDisconnect:
        manager.disconnect(code, websocket)
