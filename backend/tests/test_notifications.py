"""
Unit Tests for Notification Module
Tests WebRTC signaling, email, web push, and Discord notifications
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from notifications.webrtc_signaling import (
    WebRTCSignalingServer,
    SignalingMessageType,
    SignalingMessage,
    create_webrtc_signaling_server
)
from notifications.email_notifier import (
    EmailNotifier,
    EmailConfig,
    create_email_notifier
)
from notifications.web_push_notifier import (
    WebPushNotifier,
    PushSubscription,
    create_web_push_notifier
)
from notifications.discord_notifier import (
    DiscordNotifier,
    DiscordWebhookConfig,
    DiscordColor,
    create_discord_notifier
)


# ============================================================================
# WebRTC Signaling Tests
# ============================================================================

class TestWebRTCSignaling:
    """Test WebRTC signaling server."""
    
    def test_create_signaling_server(self):
        """Test creating signaling server."""
        server = create_webrtc_signaling_server()
        
        assert server is not None
        assert len(server.sessions) == 0
        assert len(server.peers) == 0
    
    @pytest.mark.asyncio
    async def test_handle_offer(self):
        """Test handling SDP offer."""
        server = WebRTCSignalingServer()
        
        message = {
            'type': 'offer',
            'session_id': 'session-123',
            'payload': {
                'sdp': 'v=0\r\no=- 123456 2 IN IP4 127.0.0.1\r\n...'
            }
        }
        
        response = await server.handle_message('peer-1', message)
        
        assert response['type'] == 'offer-received'
        assert response['session_id'] == 'session-123'
        assert response['status'] == 'success'
        
        # Verify session created
        session = server.get_session('session-123')
        assert session is not None
        assert session['peer_id'] == 'peer-1'
        assert session['state'] == 'offer-received'
        assert 'offer_sdp' in session
    
    @pytest.mark.asyncio
    async def test_handle_answer(self):
        """Test handling SDP answer."""
        server = WebRTCSignalingServer()
        
        # First create session with offer
        offer_message = {
            'type': 'offer',
            'session_id': 'session-123',
            'payload': {'sdp': 'offer-sdp'}
        }
        await server.handle_message('peer-1', offer_message)
        
        # Then send answer
        answer_message = {
            'type': 'answer',
            'session_id': 'session-123',
            'payload': {'sdp': 'answer-sdp'}
        }
        
        response = await server.handle_message('peer-1', answer_message)
        
        assert response['type'] == 'answer-received'
        assert response['status'] == 'connected'
        
        # Verify session updated
        session = server.get_session('session-123')
        assert session['state'] == 'connected'
        assert session['answer_sdp'] == 'answer-sdp'
    
    @pytest.mark.asyncio
    async def test_handle_ice_candidate(self):
        """Test handling ICE candidate."""
        server = WebRTCSignalingServer()
        
        # Create session first
        offer_message = {
            'type': 'offer',
            'session_id': 'session-123',
            'payload': {'sdp': 'offer-sdp'}
        }
        await server.handle_message('peer-1', offer_message)
        
        # Send ICE candidate
        ice_message = {
            'type': 'ice-candidate',
            'session_id': 'session-123',
            'payload': {
                'candidate': {
                    'candidate': 'candidate:1 1 UDP 2130706431 192.168.1.1 54321 typ host',
                    'sdpMLineIndex': 0,
                    'sdpMid': 'audio'
                }
            }
        }
        
        response = await server.handle_message('peer-1', ice_message)
        
        assert response['type'] == 'ice-candidate-received'
        assert response['status'] == 'success'
        
        # Verify candidate stored
        session = server.get_session('session-123')
        assert len(session['ice_candidates']) == 1
    
    @pytest.mark.asyncio
    async def test_handle_close(self):
        """Test handling session close."""
        server = WebRTCSignalingServer()
        
        # Create session
        offer_message = {
            'type': 'offer',
            'session_id': 'session-123',
            'payload': {'sdp': 'offer-sdp'}
        }
        await server.handle_message('peer-1', offer_message)
        
        # Close session
        close_message = {
            'type': 'close',
            'session_id': 'session-123',
            'payload': {}
        }
        
        response = await server.handle_message('peer-1', close_message)
        
        assert response['type'] == 'session-closed'
        assert response['status'] == 'success'
        
        # Verify session marked as closed
        session = server.get_session('session-123')
        assert session['state'] == 'closed'
    
    @pytest.mark.asyncio
    async def test_event_handlers(self):
        """Test event handler callbacks."""
        server = WebRTCSignalingServer()
        
        # Track handler calls
        handler_calls = []
        
        async def on_offer(msg):
            handler_calls.append(('offer', msg.session_id))
        
        async def on_answer(msg):
            handler_calls.append(('answer', msg.session_id))
        
        server.set_handlers(on_offer=on_offer, on_answer=on_answer)
        
        # Send offer
        await server.handle_message('peer-1', {
            'type': 'offer',
            'session_id': 'session-123',
            'payload': {'sdp': 'offer-sdp'}
        })
        
        # Send answer
        await server.handle_message('peer-1', {
            'type': 'answer',
            'session_id': 'session-123',
            'payload': {'sdp': 'answer-sdp'}
        })
        
        assert len(handler_calls) == 2
        assert handler_calls[0] == ('offer', 'session-123')
        assert handler_calls[1] == ('answer', 'session-123')
    
    def test_get_active_sessions(self):
        """Test getting active sessions."""
        server = WebRTCSignalingServer()
        
        # Create multiple sessions
        server.sessions['session-1'] = {'state': 'connected'}
        server.sessions['session-2'] = {'state': 'offer-received'}
        server.sessions['session-3'] = {'state': 'closed'}
        
        active = server.get_active_sessions()
        
        assert len(active) == 2
        assert 'session-1' in active
        assert 'session-2' in active
        assert 'session-3' not in active


# ============================================================================
# Email Notifier Tests
# ============================================================================

class TestEmailNotifier:
    """Test email notification system."""
    
    def test_create_email_notifier(self):
        """Test creating email notifier."""
        notifier = create_email_notifier(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="password",
            from_email="noreply@example.com"
        )
        
        assert notifier is not None
        assert notifier.config.smtp_host == "smtp.example.com"
        assert notifier.config.smtp_port == 587
    
    @pytest.mark.asyncio
    async def test_send_email(self):
        """Test sending email."""
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="password",
            from_email="noreply@example.com"
        )
        notifier = EmailNotifier(config)
        
        # Mock SMTP send
        with patch.object(notifier, '_send_smtp', new_callable=AsyncMock) as mock_send:
            result = await notifier.send_email(
                to_email="customer@example.com",
                subject="Test Email",
                body_text="This is a test email"
            )
            
            assert result is True
            assert notifier.sent_count == 1
            assert mock_send.called
    
    @pytest.mark.asyncio
    async def test_send_appointment_confirmation(self):
        """Test sending appointment confirmation."""
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="password",
            from_email="noreply@example.com"
        )
        notifier = EmailNotifier(config)
        
        with patch.object(notifier, '_send_smtp', new_callable=AsyncMock):
            result = await notifier.send_appointment_confirmation(
                to_email="customer@example.com",
                customer_name="John Smith",
                appointment_time="Tomorrow at 2:00 PM",
                service_type="HVAC Repair",
                technician_name="Mike Johnson"
            )
            
            assert result is True
            assert notifier.sent_count == 1
    
    @pytest.mark.asyncio
    async def test_send_email_failure(self):
        """Test email send failure."""
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="password",
            from_email="noreply@example.com"
        )
        notifier = EmailNotifier(config)
        
        # Mock SMTP send to raise exception
        with patch.object(notifier, '_send_smtp', side_effect=Exception("SMTP error")):
            result = await notifier.send_email(
                to_email="customer@example.com",
                subject="Test Email",
                body_text="This is a test email"
            )
            
            assert result is False
            assert notifier.failed_count == 1
    
    def test_email_stats(self):
        """Test email statistics."""
        config = EmailConfig(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="password",
            from_email="noreply@example.com"
        )
        notifier = EmailNotifier(config)
        
        notifier.sent_count = 95
        notifier.failed_count = 5
        
        stats = notifier.get_stats()
        
        assert stats['sent'] == 95
        assert stats['failed'] == 5
        assert stats['success_rate'] == 0.95


# ============================================================================
# Web Push Notifier Tests
# ============================================================================

class TestWebPushNotifier:
    """Test web push notification system."""
    
    def test_create_web_push_notifier(self):
        """Test creating web push notifier."""
        notifier = create_web_push_notifier(
            vapid_private_key="private-key",
            vapid_public_key="public-key",
            vapid_subject="mailto:admin@example.com"
        )
        
        assert notifier is not None
        assert notifier.vapid_private_key == "private-key"
        assert notifier.vapid_public_key == "public-key"
    
    def test_add_subscription(self):
        """Test adding push subscription."""
        notifier = WebPushNotifier()
        
        subscription = notifier.add_subscription(
            user_id="user-123",
            endpoint="https://fcm.googleapis.com/fcm/send/...",
            keys={
                "p256dh": "key1",
                "auth": "key2"
            }
        )
        
        assert subscription.user_id == "user-123"
        assert subscription.endpoint.startswith("https://")
        assert len(notifier.subscriptions) == 1
    
    def test_remove_subscription(self):
        """Test removing push subscription."""
        notifier = WebPushNotifier()
        
        notifier.add_subscription(
            user_id="user-123",
            endpoint="https://fcm.googleapis.com/fcm/send/...",
            keys={"p256dh": "key1", "auth": "key2"}
        )
        
        result = notifier.remove_subscription("user-123")
        
        assert result is True
        assert len(notifier.subscriptions) == 0
    
    @pytest.mark.asyncio
    async def test_send_notification(self):
        """Test sending push notification."""
        notifier = WebPushNotifier()
        
        notifier.add_subscription(
            user_id="user-123",
            endpoint="https://fcm.googleapis.com/fcm/send/...",
            keys={"p256dh": "key1", "auth": "key2"}
        )
        
        # Mock push service send
        with patch.object(notifier, '_send_to_push_service', new_callable=AsyncMock):
            result = await notifier.send_notification(
                user_id="user-123",
                title="Test Notification",
                body="This is a test"
            )
            
            assert result is True
            assert notifier.sent_count == 1
    
    @pytest.mark.asyncio
    async def test_send_job_assignment_notification(self):
        """Test sending job assignment notification."""
        notifier = WebPushNotifier()
        
        notifier.add_subscription(
            user_id="tech-123",
            endpoint="https://fcm.googleapis.com/fcm/send/...",
            keys={"p256dh": "key1", "auth": "key2"}
        )
        
        with patch.object(notifier, '_send_to_push_service', new_callable=AsyncMock):
            result = await notifier.send_job_assignment_notification(
                user_id="tech-123",
                job_id="job-456",
                service_type="HVAC Repair",
                customer_name="John Smith",
                scheduled_time="2:00 PM"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_notification_no_subscription(self):
        """Test sending notification with no subscription."""
        notifier = WebPushNotifier()
        
        result = await notifier.send_notification(
            user_id="user-999",
            title="Test",
            body="Test"
        )
        
        assert result is False
    
    def test_push_stats(self):
        """Test push notification statistics."""
        notifier = WebPushNotifier()
        
        notifier.add_subscription("user-1", "endpoint-1", {})
        notifier.add_subscription("user-2", "endpoint-2", {})
        notifier.sent_count = 48
        notifier.failed_count = 2
        
        stats = notifier.get_stats()
        
        assert stats['sent'] == 48
        assert stats['failed'] == 2
        assert stats['active_subscriptions'] == 2
        assert stats['success_rate'] == 0.96


# ============================================================================
# Discord Notifier Tests
# ============================================================================

class TestDiscordNotifier:
    """Test Discord webhook notification system."""
    
    def test_create_discord_notifier(self):
        """Test creating Discord notifier."""
        notifier = create_discord_notifier(
            webhook_url="https://discord.com/api/webhooks/...",
            username="Test Bot"
        )
        
        assert notifier is not None
        assert notifier.config.username == "Test Bot"
    
    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending Discord message."""
        config = DiscordWebhookConfig(
            webhook_url="https://discord.com/api/webhooks/..."
        )
        notifier = DiscordNotifier(config)
        
        # Mock HTTP POST
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 204
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await notifier.send_message(
                content="Test message"
            )
            
            assert result is True
            assert notifier.sent_count == 1
    
    def test_create_embed(self):
        """Test creating Discord embed."""
        config = DiscordWebhookConfig(
            webhook_url="https://discord.com/api/webhooks/..."
        )
        notifier = DiscordNotifier(config)
        
        embed = notifier.create_embed(
            title="Test Embed",
            description="Test description",
            color=DiscordColor.INFO,
            fields=[
                {'name': 'Field 1', 'value': 'Value 1', 'inline': True}
            ],
            footer="Test footer"
        )
        
        assert embed['title'] == "Test Embed"
        assert embed['description'] == "Test description"
        assert embed['color'] == DiscordColor.INFO.value
        assert len(embed['fields']) == 1
        assert embed['footer']['text'] == "Test footer"
    
    @pytest.mark.asyncio
    async def test_send_new_lead_alert(self):
        """Test sending new lead alert."""
        config = DiscordWebhookConfig(
            webhook_url="https://discord.com/api/webhooks/..."
        )
        notifier = DiscordNotifier(config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 204
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await notifier.send_new_lead_alert(
                lead_id="lead-123",
                customer_name="John Smith",
                service_type="HVAC Repair",
                urgency="emergency",
                description="Furnace stopped working",
                location="123 Main St"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_daily_summary(self):
        """Test sending daily summary."""
        config = DiscordWebhookConfig(
            webhook_url="https://discord.com/api/webhooks/..."
        )
        notifier = DiscordNotifier(config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 204
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await notifier.send_daily_summary(
                date="2024-01-15",
                total_jobs=25,
                completed_jobs=23,
                revenue=5750.00,
                technician_utilization=0.85,
                first_time_fix_rate=0.92
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_message_rate_limited(self):
        """Test handling rate limit."""
        config = DiscordWebhookConfig(
            webhook_url="https://discord.com/api/webhooks/..."
        )
        notifier = DiscordNotifier(config)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 429  # Rate limited
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await notifier.send_message(
                content="Test message"
            )
            
            assert result is False
    
    def test_discord_stats(self):
        """Test Discord notification statistics."""
        config = DiscordWebhookConfig(
            webhook_url="https://discord.com/api/webhooks/..."
        )
        notifier = DiscordNotifier(config)
        
        notifier.sent_count = 100
        notifier.failed_count = 0
        
        stats = notifier.get_stats()
        
        assert stats['sent'] == 100
        assert stats['failed'] == 0
        assert stats['success_rate'] == 1.0
