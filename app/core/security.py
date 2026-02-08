"""
Security utilities for authentication.

Handles password hashing (bcrypt) and JWT token creation/validation.
All tokens are signed with the SECRET_KEY from settings.

Usage:
    # Hash a password for storage
    hashed = hash_password("user_password")
    
    # Verify a password against hash
    if verify_password("user_password", hashed):
        print("Valid!")
    
    # Create JWT token
    token = create_access_token({"sub": str(user.id)})
    
    # Decode and validate token
    payload = decode_token(token)
    if payload:
        user_id = payload.get("sub")
"""

from datetime import datetime, timedelta, UTC
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.core.config import get_settings

settings = get_settings()

# Bcrypt context for password hashing
# "auto" handles deprecated hash migration automatically
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt hash.
    
    Args:
        plain_password: The password to verify
        hashed_password: The bcrypt hash to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hash string (includes salt)
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT access token.
    
    Args:
        data: Payload data (typically {"sub": user_id})
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT string
        
    Note:
        Default expiration is ACCESS_TOKEN_EXPIRE_MINUTES from settings.
        Token is signed with SECRET_KEY using HS256 algorithm.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict | None:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None
