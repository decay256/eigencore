from sqlalchemy import Column, DateTime, ForeignKey, Uuid, Integer
from sqlalchemy.sql import func
from app.db.database import Base
import uuid


class RoomPlayer(Base):
    """Junction table linking rooms to players."""
    __tablename__ = "room_players"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    room_id = Column(Uuid, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    slot = Column(Integer, nullable=True)  # Optional: player slot/position in the room
