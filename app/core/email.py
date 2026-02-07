"""
Email service for sending verification and password reset emails.
Supports SMTP or can be extended for SendGrid/Mailgun/etc.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import secrets
from datetime import datetime, timedelta, UTC

from app.core.config import get_settings

settings = get_settings()


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
    Send an email via SMTP.
    Returns True if successful, False otherwise.
    """
    if not settings.smtp_host:
        print(f"[EMAIL] SMTP not configured. Would send to {to_email}: {subject}")
        print(f"[EMAIL] Content: {text_content or html_content[:200]}")
        return True  # Pretend success in dev mode
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = settings.smtp_from_email or settings.smtp_username
        message["To"] = to_email
        
        # Add plain text version
        if text_content:
            message.attach(MIMEText(text_content, "plain"))
        
        # Add HTML version
        message.attach(MIMEText(html_content, "html"))
        
        # Create secure connection
        context = ssl.create_default_context()
        
        if settings.smtp_port == 465:
            # SSL
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as server:
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(message["From"], to_email, message.as_string())
        else:
            # TLS (port 587) or plain
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_port == 587:
                    server.starttls(context=context)
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(message["From"], to_email, message.as_string())
        
        return True
    except Exception as e:
        print(f"[EMAIL] Failed to send email: {e}")
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
