from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.database import Base
import uuid
import secrets
import string


def generate_room_code(length: int = 6) -> str:
    """Generate a human-friendly room code (no ambiguous chars)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No I, O, 0, 1
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Room code (what players enter to join)
    code = Column(String(10), unique=True, index=True, nullable=False, default=generate_room_code)
    
    # Game identification
    game_id = Column(String(100), nullable=False, index=True)
    
    # Host
    host_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Room config
    max_players = Column(Integer, default=2)
    is_private = Column(Boolean, default=False)
    
    # Room state
    status = Column(String(20), default="waiting")  # waiting, playing, finished
    player_ids = Column(Text, nullable=True)  # JSON array of player UUIDs
    room_data = Column(Text, nullable=True)  # JSON - game-specific room state
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # Auto-cleanup
