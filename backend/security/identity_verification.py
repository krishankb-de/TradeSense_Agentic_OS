"""Identity verification via email and phone."""

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


# In-memory storage for verification codes (use Redis in production)
_verification_codes: Dict[str, Dict] = {}


def generate_verification_code(length: int = 6) -> str:
    """
    Generate random verification code.
    
    Args:
        length: Length of verification code (default: 6)
        
    Returns:
        Random alphanumeric verification code
    """
    return ''.join(random.choices(string.digits, k=length))


def store_verification_code(
    identifier: str,
    code: str,
    expiry_minutes: int = 10
) -> None:
    """
    Store verification code with expiration.
    
    Args:
        identifier: Email or phone number
        code: Verification code
        expiry_minutes: Minutes until code expires
    """
    # Hash the code for storage
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    
    _verification_codes[identifier] = {
        "code_hash": code_hash,
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=expiry_minutes),
        "attempts": 0
    }


def verify_code(identifier: str, code: str, max_attempts: int = 3) -> bool:
    """
    Verify a verification code.
    
    Args:
        identifier: Email or phone number
        code: Verification code to check
        max_attempts: Maximum verification attempts allowed
        
    Returns:
        True if code is valid, False otherwise
    """
    if identifier not in _verification_codes:
        return False
    
    stored = _verification_codes[identifier]
    
    # Check if expired
    if datetime.now(timezone.utc) > stored["expires_at"]:
        del _verification_codes[identifier]
        return False
    
    # Increment attempts first
    stored["attempts"] += 1
    
    # Check attempts after incrementing (>= because we want to remove on the max_attempts-th try)
    if stored["attempts"] >= max_attempts:
        # Verify code one last time before removing
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        is_valid = code_hash == stored["code_hash"]
        # Remove regardless of whether code is valid
        del _verification_codes[identifier]
        return is_valid
    
    # Verify code (still have attempts left)
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    
    if code_hash == stored["code_hash"]:
        # Code is valid, remove it
        del _verification_codes[identifier]
        return True
    
    return False


def send_verification_email(
    email: str,
    code: str,
    subject: str = "TradeSense Verification Code"
) -> bool:
    """
    Send verification code via email.
    
    Args:
        email: Recipient email address
        code: Verification code to send
        subject: Email subject line
        
    Returns:
        True if email sent successfully, False otherwise
    """
    # Email configuration from environment
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("FROM_EMAIL", smtp_user)
    
    if not smtp_user or not smtp_password:
        print("WARNING: SMTP credentials not configured. Email not sent.")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = email
        
        # Email body
        text = f"""
        Your TradeSense verification code is: {code}
        
        This code will expire in 10 minutes.
        
        If you did not request this code, please ignore this email.
        """
        
        html = f"""
        <html>
          <body>
            <h2>TradeSense Verification</h2>
            <p>Your verification code is:</p>
            <h1 style="color: #2563eb; letter-spacing: 0.5em;">{code}</h1>
            <p>This code will expire in 10 minutes.</p>
            <p style="color: #6b7280; font-size: 0.875rem;">
              If you did not request this code, please ignore this email.
            </p>
          </body>
        </html>
        """
        
        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_email, email, msg.as_string())
        
        return True
        
    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False


def send_verification_sms(phone: str, code: str) -> bool:
    """
    Send verification code via SMS.
    
    Args:
        phone: Recipient phone number
        code: Verification code to send
        
    Returns:
        True if SMS sent successfully, False otherwise
    """
    # SMS configuration from environment
    # This is a placeholder - integrate with Twilio, AWS SNS, or similar
    sms_provider = os.getenv("SMS_PROVIDER", "")
    
    if not sms_provider:
        print("WARNING: SMS provider not configured. SMS not sent.")
        return False
    
    try:
        # Placeholder for SMS integration
        # In production, integrate with Twilio, AWS SNS, etc.
        message = f"Your TradeSense verification code is: {code}. Valid for 10 minutes."
        
        # TODO: Implement actual SMS sending
        print(f"SMS to {phone}: {message}")
        
        return True
        
    except Exception as e:
        print(f"Error sending verification SMS: {e}")
        return False


def initiate_email_verification(email: str) -> Optional[str]:
    """
    Initiate email verification process.
    
    Args:
        email: Email address to verify
        
    Returns:
        Verification code if successful, None otherwise
    """
    code = generate_verification_code()
    store_verification_code(email, code)
    
    if send_verification_email(email, code):
        return code
    
    return None


def initiate_phone_verification(phone: str) -> Optional[str]:
    """
    Initiate phone verification process.
    
    Args:
        phone: Phone number to verify
        
    Returns:
        Verification code if successful, None otherwise
    """
    code = generate_verification_code()
    store_verification_code(phone, code)
    
    if send_verification_sms(phone, code):
        return code
    
    return None


def cleanup_expired_codes() -> int:
    """
    Remove expired verification codes from storage.
    
    Returns:
        Number of codes removed
    """
    now = datetime.now(timezone.utc)
    expired = [
        identifier
        for identifier, data in _verification_codes.items()
        if now > data["expires_at"]
    ]
    
    for identifier in expired:
        del _verification_codes[identifier]
    
    return len(expired)
