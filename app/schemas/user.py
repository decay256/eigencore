from pydantic import BaseModel, EmailStr, computed_field
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    username: str | None = None  # Alias for display_name (frontend compatibility)
    display_name: str | None = None
    
    def get_display_name(self) -> str:
        """Return display_name or username, preferring display_name."""
        return self.display_name or self.username or self.email.split("@")[0]


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: UUID
    email: str | None
    display_name: str
    avatar_url: str | None
    oauth_provider: str | None
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserConfigUpdate(BaseModel):
    config: dict
