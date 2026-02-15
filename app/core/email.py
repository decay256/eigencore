"""
Email service for sending verification and password reset emails.
Uses Resend API for reliable email delivery.
"""
import os
import requests
from typing import Optional
import secrets
import logging
from datetime import datetime, timedelta, UTC

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(32)


def get_token_expiry(hours: int = 24) -> datetime:
    """Get expiry datetime for a token."""
    return datetime.now(UTC) + timedelta(hours=hours)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """
    Send an email via Resend API.
    Returns True if successful, False otherwise.
    """
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL", "EigenCore <onboarding@resend.dev>")
    
    if not api_key:
        logger.warning(f"[EMAIL] Resend API key not configured. Would send to {to_email}: {subject}")
        logger.info(f"[EMAIL] Content: {text_content or html_content[:200]}")
        return True  # Pretend success in dev mode
    
    try:
        payload = {
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        
        if text_content:
            payload["text"] = text_content
        
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"[EMAIL] Email sent successfully to {to_email}: {result.get('id')}")
            return True
        else:
            logger.error(f"[EMAIL] Failed to send email: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"[EMAIL] Error sending email to {to_email}: {e}")
        return False


async def send_verification_email(to_email: str, token: str, base_url: str) -> bool:
    """Send email verification email."""
    verify_url = f"{base_url}/verify-email?token={token}"
    
    subject = "Verify your Eigencore account"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #ffffff; padding: 40px; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .logo {{ font-size: 24px; font-weight: bold; margin-bottom: 30px; }}
            .logo span {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
            .footer {{ margin-top: 40px; color: #8b8b9a; font-size: 14px; }}
            a {{ color: #6366f1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">Eigencore<span>ID</span></div>
            <h2>Verify your email</h2>
            <p>Thanks for signing up! Click the button below to verify your email address:</p>
            <a href="{verify_url}" class="button">Verify Email</a>
            <p>Or copy this link: <a href="{verify_url}">{verify_url}</a></p>
            <p>This link expires in 24 hours.</p>
            <div class="footer">
                <p>If you didn't create an account, you can ignore this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Verify your Eigencore account
    
    Thanks for signing up! Click the link below to verify your email:
    {verify_url}
    
    This link expires in 24 hours.
    
    If you didn't create an account, you can ignore this email.
    """
    
    return await send_email(to_email, subject, html_content, text_content)


async def send_password_reset_email(to_email: str, token: str, base_url: str) -> bool:
    """Send password reset email."""
    reset_url = f"{base_url}/reset-password?token={token}"
    
    subject = "Reset your Eigencore password"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #ffffff; padding: 40px; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .logo {{ font-size: 24px; font-weight: bold; margin-bottom: 30px; }}
            .logo span {{ background: linear-gradient(135deg, #6366f1, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
            .button {{ display: inline-block; background: linear-gradient(135deg, #6366f1, #8b5cf6); color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
            .footer {{ margin-top: 40px; color: #8b8b9a; font-size: 14px; }}
            a {{ color: #6366f1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="logo">Eigencore<span>ID</span></div>
            <h2>Reset your password</h2>
            <p>We received a request to reset your password. Click the button below:</p>
            <a href="{reset_url}" class="button">Reset Password</a>
            <p>Or copy this link: <a href="{reset_url}">{reset_url}</a></p>
            <p>This link expires in 1 hour.</p>
            <div class="footer">
                <p>If you didn't request a password reset, you can ignore this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Reset your Eigencore password
    
    We received a request to reset your password. Click the link below:
    {reset_url}
    
    This link expires in 1 hour.
    
    If you didn't request a password reset, you can ignore this email.
    """
    
    return await send_email(to_email, subject, html_content, text_content)
