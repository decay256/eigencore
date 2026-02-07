from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str


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
