"""
Email service using Resend API for EigenCore.

Handles:
- Password reset emails
- Email verification
- Welcome emails
"""

import os
import json
import requests
from typing import Optional
import logging
from jinja2 import Template

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.api_key = os.getenv("RESEND_API_KEY")
        self.from_email = os.getenv("RESEND_FROM_EMAIL", "EigenCore <onboarding@resend.dev>")
        self.base_url = os.getenv("FRONTEND_URL", "https://core.dk-eigenvektor.de")
        
        if not self.api_key:
            logger.warning("RESEND_API_KEY not set - email service disabled")
    
    def _send_email(
        self, 
        to: str, 
        subject: str, 
        html_content: str, 
        text_content: Optional[str] = None
    ) -> bool:
        """Send email via Resend API."""
        if not self.api_key:
            logger.error("Cannot send email - no API key configured")
            return False
        
        try:
            payload = {
                "from": self.from_email,
                "to": [to],
                "subject": subject,
                "html": html_content
            }
            
            if text_content:
                payload["text"] = text_content
            
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Email sent successfully: {result.get('id')}")
                return True
            else:
                logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    def send_password_reset(self, email: str, reset_token: str) -> bool:
        """Send password reset email with token."""
        reset_url = f"{self.base_url}/reset-password?token={reset_token}"
        
        html_template = Template("""
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <h2 style="color: #333;">🔒 Password Reset Request</h2>
            
            <p>Someone requested a password reset for your EigenCore account.</p>
            
            <p>Click the button below to reset your password:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{ reset_url }}" 
                   style="background: #007bff; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Reset Password
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                Or copy this link: <br>
                <a href="{{ reset_url }}">{{ reset_url }}</a>
            </p>
            
            <hr style="margin: 30px 0; border: 1px solid #eee;">
            
            <p style="color: #999; font-size: 12px;">
                This link will expire in 1 hour. If you didn't request this reset, ignore this email.
            </p>
        </div>
        """)
        
        html_content = html_template.render(reset_url=reset_url)
        
        text_content = f"""
        Password Reset Request
        
        Someone requested a password reset for your EigenCore account.
        
        Visit this link to reset your password:
        {reset_url}
        
        This link will expire in 1 hour. If you didn't request this reset, ignore this email.
        """
        
        return self._send_email(
            to=email,
            subject="EigenCore - Reset Your Password",
            html_content=html_content,
            text_content=text_content
        )
    
    def send_email_verification(self, email: str, verification_token: str) -> bool:
        """Send email verification with token."""
        verify_url = f"{self.base_url}/verify-email?token={verification_token}"
        
        html_template = Template("""
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <h2 style="color: #333;">🎉 Welcome to EigenCore!</h2>
            
            <p>Thanks for signing up! Please verify your email address to complete registration.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{ verify_url }}" 
                   style="background: #28a745; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            
            <p style="color: #666; font-size: 14px;">
                Or copy this link: <br>
                <a href="{{ verify_url }}">{{ verify_url }}</a>
            </p>
            
            <hr style="margin: 30px 0; border: 1px solid #eee;">
            
            <p style="color: #999; font-size: 12px;">
                This link will expire in 24 hours. If you didn't sign up, ignore this email.
            </p>
        </div>
        """)
        
        html_content = html_template.render(verify_url=verify_url)
        
        text_content = f"""
        Welcome to EigenCore!
        
        Thanks for signing up! Please verify your email address to complete registration.
        
        Visit this link to verify your email:
        {verify_url}
        
        This link will expire in 24 hours. If you didn't sign up, ignore this email.
        """
        
        return self._send_email(
            to=email,
            subject="EigenCore - Verify Your Email",
            html_content=html_content,
            text_content=text_content
        )
    
    def send_welcome_email(self, email: str, username: str) -> bool:
        """Send welcome email after successful verification."""
        html_template = Template("""
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <h2 style="color: #333;">🚀 Welcome to EigenCore, {{ username }}!</h2>
            
            <p>Your account is now verified and ready to use.</p>
            
            <h3>What's next?</h3>
            <ul>
                <li>🎮 Complete your profile</li>
                <li>🎯 Explore game features</li>
                <li>🤝 Connect with other players</li>
            </ul>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{ base_url }}" 
                   style="background: #007bff; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Start Playing
                </a>
            </div>
            
            <hr style="margin: 30px 0; border: 1px solid #eee;">
            
            <p style="color: #999; font-size: 12px;">
                Need help? Contact us at support@dk-eigenvektor.de
            </p>
        </div>
        """)
        
        html_content = html_template.render(username=username, base_url=self.base_url)
        
        return self._send_email(
            to=email,
            subject="Welcome to EigenCore!",
            html_content=html_content
        )


# Global email service instance
email_service = EmailService()