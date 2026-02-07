from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Uuid
from sqlalchemy.sql import func
from app.db.database import Base
import uuid


class GameState(Base):
    __tablename__ = "game_states"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False, index=True)
    
    # Game identification
    game_id = Column(String(100), nullable=False, index=True)  # e.g., "plant-simulator", "dicpic"
    slot_name = Column(String(100), default="default")  # Save slot name
    
    # State data (JSON)
    state_data = Column(Text, nullable=False)  # JSON - plants, geometry, hormones, etc.
    
    # Metadata
    version = Column(String(50), nullable=True)  # Game version for migration
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
