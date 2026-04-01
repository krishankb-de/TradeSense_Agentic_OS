"""
Notification API Endpoints
Handles web push, email, and Discord notifications

Validates: Requirements 4.8, 4.9
"""

import logging
from typing import List, Optional
import os

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, EmailStr

from notifications import (
    create_email_notifier,
    create_web_push_notifier,
    create_discord_notifier,
    EmailNotifier,
    WebPushNotifier,
    DiscordNotifier
)
from security.auth import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class SendEmailRequest(BaseModel):
    """Request model for sending email."""
    to_email: EmailStr = Field(..., description="Recipient email")
    subject: str = Field(..., description="Email subject")
    body_text: str = Field(..., description="Plain text body")
    body_html: Optional[str] = Field(None, description="HTML body")


class SendPushRequest(BaseModel):
    """Request model for sending push notification."""
    user_id: str = Field(..., description="User ID")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    icon: Optional[str] = Field(None, description="Icon URL")
    data: Optional[dict] = Field(None, description="Custom data")


class AddPushSubscriptionRequest(BaseModel):
    """Request model for adding push subscription."""
    endpoint: str = Field(..., description="Push service endpoint")
    keys: dict = Field(..., description="Encryption keys (p256dh and auth)")


class SendDiscordRequest(BaseModel):
    """Request model for sending Discord notification."""
    content: Optional[str] = Field(None, description="Message content")
    embeds: Optional[List[dict]] = Field(None, description="Embed objects")


class NotificationResponse(BaseModel):
    """Response model for notification."""
    success: bool = Field(..., description="Whether notification was sent")
    message: str = Field(..., description="Status message")


class SubscriptionResponse(BaseModel):
    """Response model for subscription."""
    user_id: str
    endpoint: str
    created_at: str


# ============================================================================
# Dependency Injection
# ============================================================================

def get_email_notifier() -> Optional[EmailNotifier]:
    """Get email notifier instance."""
    if not os.getenv("SMTP_HOST"):
        return None
    
    try:
        return create_email_notifier(
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            from_email=os.getenv("FROM_EMAIL", "noreply@tradesense.com"),
            from_name=os.getenv("FROM_NAME", "TradeSense"),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        )
    except Exception as e:
        logger.error(f"Failed to create email notifier: {e}")
        return None


def get_push_notifier() -> Optional[WebPushNotifier]:
    """Get web push notifier instance."""
    if not os.getenv("VAPID_PRIVATE_KEY"):
        return None
    
    try:
        return create_web_push_notifier(
            vapid_private_key=os.getenv("VAPID_PRIVATE_KEY"),
            vapid_public_key=os.getenv("VAPID_PUBLIC_KEY"),
            vapid_subject=os.getenv("VAPID_SUBJECT", "mailto:admin@tradesense.com")
        )
    except Exception as e:
        logger.error(f"Failed to create push notifier: {e}")
        return None


def get_discord_notifier() -> Optional[DiscordNotifier]:
    """Get Discord notifier instance."""
    if not os.getenv("DISCORD_WEBHOOK_URL"):
        return None
    
    try:
        return create_discord_notifier(
            webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
            username=os.getenv("DISCORD_BOT_USERNAME", "TradeSense Bot"),
            avatar_url=os.getenv("DISCORD_BOT_AVATAR_URL")
        )
    except Exception as e:
        logger.error(f"Failed to create Discord notifier: {e}")
        return None


# ============================================================================
# Email Endpoints
# ============================================================================

@router.post(
    "/email/send",
    response_model=NotificationResponse,
    summary="Send email notification",
    description="Send email notification to recipient"
)
async def send_email(
    request: SendEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send email notification.
    
    Validates: Requirement 4.8 (Email notifications)
    """
    email_notifier = get_email_notifier()
    
    if not email_notifier:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service not configured"
        )
    
    try:
        success = await email_notifier.send_email(
            to_email=request.to_email,
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html
        )
        
        return NotificationResponse(
            success=success,
            message="Email sent successfully" if success else "Failed to send email"
        )
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )


@router.get(
    "/email/stats",
    summary="Get email statistics",
    description="Get email notification statistics"
)
async def get_email_stats(
    current_user: User = Depends(get_current_user)
):
    """Get email notification statistics."""
    email_notifier = get_email_notifier()
    
    if not email_notifier:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service not configured"
        )
    
    return email_notifier.get_stats()


# ============================================================================
# Web Push Endpoints
# ============================================================================

@router.post(
    "/push/subscribe",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add push subscription",
    description="Add web push subscription for user"
)
async def add_push_subscription(
    request: AddPushSubscriptionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Add web push subscription.
    
    Validates: Requirement 4.9 (Push notifications)
    """
    push_notifier = get_push_notifier()
    
    if not push_notifier:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notification service not configured"
        )
    
    try:
        subscription = push_notifier.add_subscription(
            user_id=current_user.id,
            endpoint=request.endpoint,
            keys=request.keys
        )
        
        return SubscriptionResponse(
            user_id=subscription.user_id,
            endpoint=subscription.endpoint,
            created_at=subscription.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Failed to add push subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add push subscription: {str(e)}"
        )


@router.delete(
    "/push/subscribe",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove push subscription",
    description="Remove web push subscription for user"
)
async def remove_push_subscription(
    current_user: User = Depends(get_current_user)
):
    """
    Remove web push subscription.
    
    Validates: Requirement 4.9 (Push notifications)
    """
    push_notifier = get_push_notifier()
    
    if not push_notifier:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notification service not configured"
        )
    
    try:
        push_notifier.remove_subscription(current_user.id)
        logger.info(f"Push subscription removed for user {current_user.id}")
        
    except Exception as e:
        logger.error(f"Failed to remove push subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove push subscription: {str(e)}"
        )


@router.post(
    "/push/send",
    response_model=NotificationResponse,
    summary="Send push notification",
    description="Send web push notification to user"
)
async def send_push_notification(
    request: SendPushRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send web push notification.
    
    Validates: Requirement 4.9 (Push notifications)
    """
    push_notifier = get_push_notifier()
    
    if not push_notifier:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notification service not configured"
        )
    
    try:
        success = await push_notifier.send_notification(
            user_id=request.user_id,
            title=request.title,
            body=request.body,
            icon=request.icon,
            data=request.data
        )
        
        return NotificationResponse(
            success=success,
            message="Push notification sent successfully" if success else "Failed to send push notification"
        )
        
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send push notification: {str(e)}"
        )


@router.get(
    "/push/stats",
    summary="Get push notification statistics",
    description="Get web push notification statistics"
)
async def get_push_stats(
    current_user: User = Depends(get_current_user)
):
    """Get web push notification statistics."""
    push_notifier = get_push_notifier()
    
    if not push_notifier:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notification service not configured"
        )
    
    return push_notifier.get_stats()


# ============================================================================
# Discord Endpoints
# ============================================================================

@router.post(
    "/discord/send",
    response_model=NotificationResponse,
    summary="Send Discord notification",
    description="Send notification to Discord webhook"
)
async def send_discord_notification(
    request: SendDiscordRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Send Discord notification.
    
    Validates: Requirement 4.8 (Discord notifications)
    """
    discord_notifier = get_discord_notifier()
    
    if not discord_notifier:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discord notification service not configured"
        )
    
    try:
        success = await discord_notifier.send_message(
            content=request.content,
            embeds=request.embeds
        )
        
        return NotificationResponse(
            success=success,
            message="Discord notification sent successfully" if success else "Failed to send Discord notification"
        )
        
    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send Discord notification: {str(e)}"
        )


@router.get(
    "/discord/stats",
    summary="Get Discord notification statistics",
    description="Get Discord notification statistics"
)
async def get_discord_stats(
    current_user: User = Depends(get_current_user)
):
    """Get Discord notification statistics."""
    discord_notifier = get_discord_notifier()
    
    if not discord_notifier:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Discord notification service not configured"
        )
    
    return discord_notifier.get_stats()
