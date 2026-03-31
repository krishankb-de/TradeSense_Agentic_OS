"""
Web Push Notification System
Handles browser push notifications for technician alerts
Validates: Requirements 4.8, 4.9
"""

import logging
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class PushSubscription:
    """Web push subscription information."""
    endpoint: str
    keys: Dict[str, str]  # p256dh and auth keys
    user_id: str
    created_at: datetime


class WebPushNotifier:
    """
    Web Push Notification System.
    
    Sends browser push notifications to technicians for:
    - New job assignments
    - Schedule changes
    - Emergency alerts
    - Customer messages
    
    Features:
    - VAPID authentication
    - Payload encryption
    - Subscription management
    - Delivery tracking
    
    Validates: Requirements 4.8, 4.9
    
    Note: This is a simplified implementation. For production, use
    the 'pywebpush' library for full VAPID support and encryption.
    """
    
    def __init__(
        self,
        vapid_private_key: Optional[str] = None,
        vapid_public_key: Optional[str] = None,
        vapid_subject: Optional[str] = None
    ):
        """
        Initialize web push notifier.
        
        Args:
            vapid_private_key: VAPID private key (optional for now)
            vapid_public_key: VAPID public key (optional for now)
            vapid_subject: VAPID subject (mailto: or https:)
        """
        self.vapid_private_key = vapid_private_key
        self.vapid_public_key = vapid_public_key
        self.vapid_subject = vapid_subject
        
        # Subscription storage: user_id -> subscription
        self.subscriptions: Dict[str, PushSubscription] = {}
        
        # Statistics
        self.sent_count = 0
        self.failed_count = 0
        
        logger.info("Web Push notifier initialized")
    
    def add_subscription(
        self,
        user_id: str,
        endpoint: str,
        keys: Dict[str, str]
    ) -> PushSubscription:
        """
        Add push subscription for a user.
        
        Args:
            user_id: User identifier
            endpoint: Push service endpoint URL
            keys: Encryption keys (p256dh and auth)
            
        Returns:
            Created subscription
        """
        subscription = PushSubscription(
            endpoint=endpoint,
            keys=keys,
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        
        self.subscriptions[user_id] = subscription
        
        logger.info(f"Added push subscription for user {user_id}")
        
        return subscription
    
    def remove_subscription(self, user_id: str) -> bool:
        """
        Remove push subscription for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if removed, False if not found
        """
        if user_id in self.subscriptions:
            del self.subscriptions[user_id]
            logger.info(f"Removed push subscription for user {user_id}")
            return True
        return False
    
    def get_subscription(self, user_id: str) -> Optional[PushSubscription]:
        """
        Get push subscription for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Subscription if found, None otherwise
        """
        return self.subscriptions.get(user_id)
    
    async def send_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        icon: Optional[str] = None,
        badge: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        actions: Optional[list] = None
    ) -> bool:
        """
        Send push notification to user.
        
        Args:
            user_id: User identifier
            title: Notification title
            body: Notification body
            icon: Optional icon URL
            badge: Optional badge URL
            data: Optional custom data
            actions: Optional notification actions
            
        Returns:
            True if sent successfully, False otherwise
        """
        subscription = self.get_subscription(user_id)
        
        if not subscription:
            logger.warning(f"No push subscription found for user {user_id}")
            return False
        
        try:
            # Build notification payload
            payload = {
                'title': title,
                'body': body,
                'icon': icon or '/default-icon.png',
                'badge': badge or '/default-badge.png',
                'data': data or {},
                'timestamp': datetime.utcnow().isoformat()
            }
            
            if actions:
                payload['actions'] = actions
            
            # Send to push service
            await self._send_to_push_service(subscription, payload)
            
            self.sent_count += 1
            logger.info(f"Push notification sent to user {user_id}: {title}")
            
            return True
            
        except Exception as e:
            self.failed_count += 1
            logger.error(f"Failed to send push notification to user {user_id}: {e}")
            return False
    
    async def _send_to_push_service(
        self,
        subscription: PushSubscription,
        payload: Dict[str, Any]
    ):
        """
        Send notification to push service endpoint.
        
        Args:
            subscription: Push subscription
            payload: Notification payload
            
        Note: This is a simplified implementation. For production,
        use the 'pywebpush' library for proper VAPID authentication
        and payload encryption.
        """
        # In production, this would:
        # 1. Encrypt payload using subscription keys
        # 2. Generate VAPID authentication header
        # 3. Send POST request to subscription endpoint
        
        # For now, we'll just log the attempt
        logger.debug(
            f"Sending push to endpoint: {subscription.endpoint[:50]}... "
            f"Payload: {json.dumps(payload)[:100]}..."
        )
        
        # Simplified HTTP POST (in production, use pywebpush)
        try:
            async with aiohttp.ClientSession() as session:
                # Note: This is a placeholder. Real implementation needs:
                # - Payload encryption with p256dh key
                # - VAPID JWT authentication
                # - Proper headers (TTL, Urgency, etc.)
                
                headers = {
                    'Content-Type': 'application/json',
                    'TTL': '86400',  # 24 hours
                    'Urgency': 'normal'
                }
                
                # In production, encrypt payload here
                encrypted_payload = json.dumps(payload)
                
                async with session.post(
                    subscription.endpoint,
                    data=encrypted_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status not in [200, 201]:
                        raise Exception(
                            f"Push service returned status {response.status}"
                        )
                        
        except Exception as e:
            logger.error(f"Error sending to push service: {e}")
            raise
    
    async def send_job_assignment_notification(
        self,
        user_id: str,
        job_id: str,
        service_type: str,
        customer_name: str,
        scheduled_time: str
    ) -> bool:
        """
        Send job assignment notification to technician.
        
        Args:
            user_id: Technician user ID
            job_id: Job identifier
            service_type: Type of service
            customer_name: Customer name
            scheduled_time: Scheduled time string
            
        Returns:
            True if sent successfully
        """
        return await self.send_notification(
            user_id=user_id,
            title="New Job Assignment",
            body=f"{service_type} for {customer_name} at {scheduled_time}",
            icon="/icons/job-assignment.png",
            data={
                'type': 'job_assignment',
                'job_id': job_id,
                'service_type': service_type,
                'customer_name': customer_name,
                'scheduled_time': scheduled_time
            },
            actions=[
                {'action': 'view', 'title': 'View Details'},
                {'action': 'navigate', 'title': 'Start Navigation'}
            ]
        )
    
    async def send_emergency_alert(
        self,
        user_id: str,
        alert_message: str,
        location: str
    ) -> bool:
        """
        Send emergency alert to technician.
        
        Args:
            user_id: Technician user ID
            alert_message: Alert message
            location: Emergency location
            
        Returns:
            True if sent successfully
        """
        return await self.send_notification(
            user_id=user_id,
            title="🚨 Emergency Alert",
            body=f"{alert_message} at {location}",
            icon="/icons/emergency.png",
            badge="/icons/emergency-badge.png",
            data={
                'type': 'emergency',
                'message': alert_message,
                'location': location,
                'priority': 'high'
            },
            actions=[
                {'action': 'accept', 'title': 'Accept'},
                {'action': 'view', 'title': 'View Details'}
            ]
        )
    
    async def send_schedule_change_notification(
        self,
        user_id: str,
        change_type: str,
        details: str
    ) -> bool:
        """
        Send schedule change notification to technician.
        
        Args:
            user_id: Technician user ID
            change_type: Type of change (added, removed, rescheduled)
            details: Change details
            
        Returns:
            True if sent successfully
        """
        return await self.send_notification(
            user_id=user_id,
            title=f"Schedule {change_type.title()}",
            body=details,
            icon="/icons/schedule.png",
            data={
                'type': 'schedule_change',
                'change_type': change_type,
                'details': details
            },
            actions=[
                {'action': 'view', 'title': 'View Schedule'}
            ]
        )
    
    def get_stats(self) -> dict:
        """
        Get push notification statistics.
        
        Returns:
            Dictionary with sent/failed counts
        """
        return {
            'sent': self.sent_count,
            'failed': self.failed_count,
            'active_subscriptions': len(self.subscriptions),
            'success_rate': (
                self.sent_count / (self.sent_count + self.failed_count)
                if (self.sent_count + self.failed_count) > 0
                else 0.0
            )
        }


# Factory function
def create_web_push_notifier(
    vapid_private_key: Optional[str] = None,
    vapid_public_key: Optional[str] = None,
    vapid_subject: Optional[str] = None
) -> WebPushNotifier:
    """
    Factory function to create web push notifier.
    
    Args:
        vapid_private_key: VAPID private key
        vapid_public_key: VAPID public key
        vapid_subject: VAPID subject (mailto: or https:)
        
    Returns:
        Configured WebPushNotifier instance
    """
    return WebPushNotifier(
        vapid_private_key=vapid_private_key,
        vapid_public_key=vapid_public_key,
        vapid_subject=vapid_subject
    )
