"""
Email Service

Handles sending verification codes and password reset links.
Uses SMTP for email delivery.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

# SMTP Configuration from environment
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@aiagentbuilder.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def send_verification_email(email: str, code: str) -> bool:
    """
    Send email verification code to user.
    
    Args:
        email: User email address
        code: 6-digit verification code
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        subject = "Verify Your Email - Flowora"

        verification_link = f"{FRONTEND_URL}/verify-email?token={code}"

        if not SMTP_HOST or not SMTP_USER:
            logger.warning(
                "SMTP not configured. Verification link for %s: %s",
                email,
                verification_link
            )
            return False
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Welcome to Flowora!</h2>
                <p>Click the button below to verify your email:</p>
                <p>
                  <a href="{verification_link}" style="background-color: #2563eb; color: white; padding: 10px 18px; text-decoration: none; border-radius: 6px;">
                    Verify Email
                  </a>
                </p>
                <p style="color: #666;">Or paste this link in your browser:</p>
                <p style="color: #666; word-break: break-all;">{verification_link}</p>
                <p style="color: #999; font-size: 12px;">This link will expire in 30 minutes.</p>
                <p style="color: #999; font-size: 12px;">If you didn't sign up, please ignore this email.</p>
            </body>
        </html>
        """
        
        _send_email(email, subject, html_body)
        logger.info(f"Verification email sent to {email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send verification email to {email}: {e}")
        return False


def send_password_reset_email(email: str, reset_token: str) -> bool:
    """
    Send password reset link to user.
    
    Args:
        email: User email address
        reset_token: Secure reset token (not hashed)
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
        subject = "Reset Your Password - Flowora"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Password Reset Request</h2>
                <p>Click the link below to reset your password:</p>
                <p>
                    <a href="{reset_link}" style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Reset Password
                    </a>
                </p>
                <p style="color: #666;">Or copy this link: {reset_link}</p>
                <p style="color: #999; font-size: 12px;">This link will expire in 30 minutes.</p>
                <p style="color: #999; font-size: 12px;">If you didn't request a password reset, please ignore this email.</p>
            </body>
        </html>
        """
        
        _send_email(email, subject, html_body)
        logger.info(f"Password reset email sent to {email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send password reset email to {email}: {e}")
        return False


def _send_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Internal method to send email via SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: Email body (HTML)
        
    Raises:
        Exception: If SMTP connection or send fails
    """
    if not SMTP_HOST or not SMTP_USER:
        logger.warning("SMTP not configured. Email service disabled.")
        return
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        
        # Attach HTML body
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send via SMTP
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"Email sent to {to_email}")
    
    except Exception as e:
        logger.error(f"SMTP error sending email to {to_email}: {e}")
        raise
