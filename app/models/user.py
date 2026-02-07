from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy import Uuid
from app.db.database import Base
import uuid


class User(Base):
    __tablename__ = "users"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    
    # Basic info
    email = Column(String(255), unique=True, index=True, nullable=True)
    display_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=True)  # Null for OAuth-only users
    
    # OAuth identifiers
    oauth_provider = Column(String(50), nullable=True)  # steam, discord, google
    oauth_id = Column(String(255), nullable=True, index=True)
    
    # Profile
    avatar_url = Column(Text, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # User config/preferences (JSON)
    config = Column(Text, nullable=True)  # JSON stored as text
