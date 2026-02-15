"""
Authentication routes for Eigencore.

Handles user registration, login, profile management, email verification,
and password reset flows. OAuth authentication is handled in oauth.py.

Endpoints:
    POST /register - Create new account with email/password
    POST /login - Authenticate and get JWT token
    GET /me - Get current user profile
    PATCH /me - Update profile (display_name, avatar_url)
    DELETE /me - Delete account permanently
    POST /change-password - Change password (requires current password)
    POST /verify-email - Verify email with token
    POST /resend-verification - Request new verification email
    POST /forgot-password - Request password reset email
    POST /reset-password - Reset password with token
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, UTC
from pydantic import BaseModel, EmailStr

from app.db.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, TokenResponse
from app.core.security import hash_password, verify_password, create_access_token
from app.core.email import (
    generate_token, 
    get_token_expiry, 
    send_verification_email, 
    send_password_reset_email
)
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class EmailRequest(BaseModel):
    """Request containing only an email address."""
    email: EmailStr


class VerifyEmailRequest(BaseModel):
    """Request to verify email with token from verification email."""
    token: str


class ResetPasswordRequest(BaseModel):
    """Request to reset password using token from reset email."""
    token: str
    new_password: str


class MessageResponse(BaseModel):
    """Generic success message response."""
    message: str


class UpdateProfileRequest(BaseModel):
    """Request to update user profile fields."""
    display_name: str | None = None
    avatar_url: str | None = None


class ChangePasswordRequest(BaseModel):
    """Request to change password (requires current password)."""
    current_password: str
    new_password: str


# =============================================================================
# Registration & Login
# =============================================================================

@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new user with email and password.
    
    Creates the user, sends a verification email (if SMTP configured),
    and returns a JWT token. User can authenticate immediately but
    some features may require email verification.
    
    Returns:
        TokenResponse with access_token and user info
        
    Raises:
        400: Email already registered
        422: Invalid email format or missing fields
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Generate verification token
    verification_token = generate_token()
    
    # Create user
    user = User(
        email=user_data.email,
        display_name=user_data.get_display_name(),
        password_hash=hash_password(user_data.password),
        email_verification_token=verification_token,
        email_verification_expires=get_token_expiry(hours=24),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Send verification email in background (non-blocking)
    background_tasks.add_task(
        send_verification_email,
        user.email,
        verification_token,
        settings.base_url
    )
    
    # Generate auth token
    token = create_access_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate user with email and password.
    
    Uses OAuth2 password flow (form data with 'username' and 'password').
    The 'username' field accepts the user's email address.
    
    Returns:
        TokenResponse with access_token and user info
        
    Raises:
        401: Invalid credentials or user not found
    """
    # OAuth2 spec uses 'username' field, but we accept email
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    
    # Update last login timestamp
    user.last_login = datetime.now(UTC)
    await db.commit()
    
    token = create_access_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


# =============================================================================
# Profile Management
# =============================================================================

@router.get("/me", response_model=UserResponse)
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user),
):
    """Get the current authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user),
):
    """
    Update the current user's profile.
    
    Allows updating display_name and avatar_url. Only provided fields
    are updated; omitted fields remain unchanged.
    
    Args:
        display_name: New display name (2-32 characters)
        avatar_url: URL to avatar image (must be http/https)
        
    Raises:
        400: Invalid display name length or avatar URL format
    """
    if request.display_name is not None:
        if len(request.display_name) < 2 or len(request.display_name) > 32:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Display name must be between 2 and 32 characters",
            )
        current_user.display_name = request.display_name
    
    if request.avatar_url is not None:
        if request.avatar_url and not request.avatar_url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Avatar URL must be a valid HTTP(S) URL",
            )
        current_user.avatar_url = request.avatar_url or None
    
    await db.commit()
    await db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user),
):
    """
    Change password for the current user.
    
    Requires the current password for verification. Only works for
    accounts created with email/password (not OAuth-only accounts).
    
    Raises:
        400: OAuth-only account, wrong current password, or weak new password
    """
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change password for OAuth-only accounts",
        )
    
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters",
        )
    
    current_user.password_hash = hash_password(request.new_password)
    await db.commit()
    
    return MessageResponse(message="Password changed successfully")


@router.delete("/me", response_model=MessageResponse)
async def delete_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(__import__("app.api.deps", fromlist=["get_current_user"]).get_current_user),
):
    """
    Permanently delete the current user's account.
    
    This action is irreversible. All user data including game saves
    will be deleted due to cascade rules.
    """
    await db.delete(current_user)
    await db.commit()
    
    return MessageResponse(message="Account deleted successfully")


# =============================================================================
# Email Verification
# =============================================================================

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify email address using token from verification email.
    
    Token is single-use and expires after 24 hours.
    
    Raises:
        400: Invalid or expired token
    """
    result = await db.execute(
        select(User).where(User.email_verification_token == request.token)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )
    
    if user.email_verification_expires and user.email_verification_expires < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one.",
        )
    
    # Mark as verified and clear token
    user.is_verified = True
    user.email_verification_token = None
    user.email_verification_expires = None
    await db.commit()
    
    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a new verification email.
    
    For security, always returns success even if email doesn't exist
    or is already verified (prevents email enumeration).
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    # Don't reveal if email exists or not
    if user and not user.is_verified:
        verification_token = generate_token()
        user.email_verification_token = verification_token
        user.email_verification_expires = get_token_expiry(hours=24)
        await db.commit()
        
        background_tasks.add_task(
            send_verification_email,
            user.email,
            verification_token,
            settings.frontend_url
        )
    
    return MessageResponse(message="If that email exists and is unverified, we've sent a verification link.")


# =============================================================================
# Password Reset
# =============================================================================

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Request a password reset email.
    
    Only works for accounts with passwords (not OAuth-only).
    For security, always returns success (prevents email enumeration).
    Reset tokens expire after 1 hour.
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    
    # Only for password-based accounts, don't reveal if email exists
    if user and user.password_hash:
        reset_token = generate_token()
        user.password_reset_token = reset_token
        user.password_reset_expires = get_token_expiry(hours=1)
        await db.commit()
        
        background_tasks.add_task(
            send_password_reset_email,
            user.email,
            reset_token,
            settings.frontend_url
        )
    
    return MessageResponse(message="If that email exists, we've sent a password reset link.")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using token from reset email.
    
    Token is single-use and expires after 1 hour.
    
    Raises:
        400: Invalid or expired token
    """
    result = await db.execute(
        select(User).where(User.password_reset_token == request.token)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    
    if user.password_reset_expires and user.password_reset_expires < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one.",
        )
    
    # Update password and clear token
    user.password_hash = hash_password(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    await db.commit()
    
    return MessageResponse(message="Password reset successfully")
