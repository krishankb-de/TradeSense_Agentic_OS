"""
Notification Module
Handles WebRTC signaling, web push, email, and Discord notifications
Validates: Requirements 4.1, 4.8
"""

from .webrtc_signaling import (
    WebRTCSignalingServer,
    SignalingMessage,
    create_webrtc_signaling_server
)
from .email_notifier import (
    EmailNotifier,
    EmailConfig,
    create_email_notifier
)
from .web_push_notifier import (
    WebPushNotifier,
    PushSubscription,
    create_web_push_notifier
)
from .discord_notifier import (
    DiscordNotifier,
    DiscordWebhookConfig,
    create_discord_notifier
)

__all__ = [
    'WebRTCSignalingServer',
    'SignalingMessage',
    'create_webrtc_signaling_server',
    'EmailNotifier',
    'EmailConfig',
    'create_email_notifier',
    'WebPushNotifier',
    'PushSubscription',
    'create_web_push_notifier',
    'DiscordNotifier',
    'DiscordWebhookConfig',
    'create_discord_notifier',
]
