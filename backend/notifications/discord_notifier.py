"""
Discord Webhook Notification System
Handles Discord webhook notifications for team alerts
Validates: Requirements 4.8, 4.9
"""

import logging
import aiohttp
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DiscordColor(int, Enum):
    """Discord embed colors."""
    SUCCESS = 0x00FF00  # Green
    INFO = 0x0099FF     # Blue
    WARNING = 0xFFCC00  # Yellow
    ERROR = 0xFF0000    # Red
    EMERGENCY = 0xFF0000  # Red


@dataclass
class DiscordWebhookConfig:
    """Discord webhook configuration."""
    webhook_url: str
    username: str = "TradeSense Bot"
    avatar_url: Optional[str] = None


class DiscordNotifier:
    """
    Discord Webhook Notification System.
    
    Sends Discord notifications to team channels for:
    - New lead alerts
    - Emergency job notifications
    - System status updates
    - Daily summaries
    
    Features:
    - Rich embeds with colors
    - Mentions and role pings
    - File attachments
    - Rate limit handling
    
    Validates: Requirements 4.8, 4.9
    """
    
    def __init__(self, config: DiscordWebhookConfig):
        """
        Initialize Discord notifier.
        
        Args:
            config: Discord webhook configuration
        """
        self.config = config
        
        # Statistics
        self.sent_count = 0
        self.failed_count = 0
        
        logger.info(f"Discord notifier initialized: {config.username}")
    
    async def send_message(
        self,
        content: Optional[str] = None,
        embeds: Optional[List[Dict[str, Any]]] = None,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None
    ) -> bool:
        """
        Send message to Discord webhook.
        
        Args:
            content: Message content (plain text)
            embeds: List of embed objects
            username: Override bot username
            avatar_url: Override bot avatar
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            payload = {}
            
            if content:
                payload['content'] = content
            
            if embeds:
                payload['embeds'] = embeds
            
            if username or self.config.username:
                payload['username'] = username or self.config.username
            
            if avatar_url or self.config.avatar_url:
                payload['avatar_url'] = avatar_url or self.config.avatar_url
            
            # Send to Discord
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 204:
                        self.sent_count += 1
                        logger.info("Discord message sent successfully")
                        return True
                    elif response.status == 429:
                        # Rate limited
                        logger.warning("Discord rate limit hit")
                        return False
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Discord webhook returned status {response.status}: "
                            f"{error_text}"
                        )
                        return False
                        
        except Exception as e:
            self.failed_count += 1
            logger.error(f"Failed to send Discord message: {e}")
            return False
    
    def create_embed(
        self,
        title: str,
        description: Optional[str] = None,
        color: DiscordColor = DiscordColor.INFO,
        fields: Optional[List[Dict[str, Any]]] = None,
        footer: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        image_url: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Create Discord embed object.
        
        Args:
            title: Embed title
            description: Embed description
            color: Embed color
            fields: List of field objects
            footer: Footer text
            thumbnail_url: Thumbnail image URL
            image_url: Main image URL
            timestamp: Timestamp for embed
            
        Returns:
            Embed dictionary
        """
        embed = {
            'title': title,
            'color': color.value
        }
        
        if description:
            embed['description'] = description
        
        if fields:
            embed['fields'] = fields
        
        if footer:
            embed['footer'] = {'text': footer}
        
        if thumbnail_url:
            embed['thumbnail'] = {'url': thumbnail_url}
        
        if image_url:
            embed['image'] = {'url': image_url}
        
        if timestamp:
            embed['timestamp'] = timestamp.isoformat()
        
        return embed
    
    async def send_new_lead_alert(
        self,
        lead_id: str,
        customer_name: str,
        service_type: str,
        urgency: str,
        description: str,
        location: str
    ) -> bool:
        """
        Send new lead alert to Discord.
        
        Args:
            lead_id: Lead identifier
            customer_name: Customer name
            service_type: Type of service
            urgency: Urgency level
            description: Issue description
            location: Service location
            
        Returns:
            True if sent successfully
        """
        # Determine color based on urgency
        color = DiscordColor.INFO
        if urgency == 'emergency':
            color = DiscordColor.EMERGENCY
        elif urgency == 'urgent':
            color = DiscordColor.WARNING
        
        embed = self.create_embed(
            title=f"🆕 New Lead: {service_type}",
            description=description[:200],  # Limit description length
            color=color,
            fields=[
                {
                    'name': 'Customer',
                    'value': customer_name,
                    'inline': True
                },
                {
                    'name': 'Urgency',
                    'value': urgency.upper(),
                    'inline': True
                },
                {
                    'name': 'Location',
                    'value': location,
                    'inline': False
                },
                {
                    'name': 'Lead ID',
                    'value': f"`{lead_id}`",
                    'inline': False
                }
            ],
            footer="TradeSense Lead Management",
            timestamp=datetime.utcnow()
        )
        
        # Add mention for emergency
        content = None
        if urgency == 'emergency':
            content = "@here 🚨 Emergency lead requires immediate attention!"
        
        return await self.send_message(content=content, embeds=[embed])
    
    async def send_emergency_job_alert(
        self,
        job_id: str,
        customer_name: str,
        service_type: str,
        location: str,
        assigned_technician: Optional[str] = None
    ) -> bool:
        """
        Send emergency job alert to Discord.
        
        Args:
            job_id: Job identifier
            customer_name: Customer name
            service_type: Type of service
            location: Service location
            assigned_technician: Assigned technician name
            
        Returns:
            True if sent successfully
        """
        embed = self.create_embed(
            title="🚨 EMERGENCY JOB",
            description=f"Emergency {service_type} requires immediate dispatch",
            color=DiscordColor.EMERGENCY,
            fields=[
                {
                    'name': 'Customer',
                    'value': customer_name,
                    'inline': True
                },
                {
                    'name': 'Service Type',
                    'value': service_type,
                    'inline': True
                },
                {
                    'name': 'Location',
                    'value': location,
                    'inline': False
                },
                {
                    'name': 'Assigned Technician',
                    'value': assigned_technician or 'Not yet assigned',
                    'inline': False
                },
                {
                    'name': 'Job ID',
                    'value': f"`{job_id}`",
                    'inline': False
                }
            ],
            footer="TradeSense Emergency Dispatch",
            timestamp=datetime.utcnow()
        )
        
        content = "@here 🚨 EMERGENCY JOB - Immediate action required!"
        
        return await self.send_message(content=content, embeds=[embed])
    
    async def send_daily_summary(
        self,
        date: str,
        total_jobs: int,
        completed_jobs: int,
        revenue: float,
        technician_utilization: float,
        first_time_fix_rate: float
    ) -> bool:
        """
        Send daily summary to Discord.
        
        Args:
            date: Date string
            total_jobs: Total jobs scheduled
            completed_jobs: Jobs completed
            revenue: Total revenue
            technician_utilization: Utilization rate
            first_time_fix_rate: First-time fix rate
            
        Returns:
            True if sent successfully
        """
        embed = self.create_embed(
            title=f"📊 Daily Summary - {date}",
            description="Here's today's performance summary",
            color=DiscordColor.SUCCESS,
            fields=[
                {
                    'name': 'Jobs Completed',
                    'value': f"{completed_jobs}/{total_jobs}",
                    'inline': True
                },
                {
                    'name': 'Revenue',
                    'value': f"${revenue:,.2f}",
                    'inline': True
                },
                {
                    'name': 'Technician Utilization',
                    'value': f"{technician_utilization:.1%}",
                    'inline': True
                },
                {
                    'name': 'First-Time Fix Rate',
                    'value': f"{first_time_fix_rate:.1%}",
                    'inline': True
                }
            ],
            footer="TradeSense Analytics",
            timestamp=datetime.utcnow()
        )
        
        return await self.send_message(embeds=[embed])
    
    async def send_system_status(
        self,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send system status update to Discord.
        
        Args:
            status: Status level (success, info, warning, error)
            message: Status message
            details: Optional additional details
            
        Returns:
            True if sent successfully
        """
        # Map status to color
        color_map = {
            'success': DiscordColor.SUCCESS,
            'info': DiscordColor.INFO,
            'warning': DiscordColor.WARNING,
            'error': DiscordColor.ERROR
        }
        color = color_map.get(status.lower(), DiscordColor.INFO)
        
        # Map status to emoji
        emoji_map = {
            'success': '✅',
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌'
        }
        emoji = emoji_map.get(status.lower(), 'ℹ️')
        
        fields = []
        if details:
            for key, value in details.items():
                fields.append({
                    'name': key.replace('_', ' ').title(),
                    'value': str(value),
                    'inline': True
                })
        
        embed = self.create_embed(
            title=f"{emoji} System Status: {status.upper()}",
            description=message,
            color=color,
            fields=fields if fields else None,
            footer="TradeSense System Monitor",
            timestamp=datetime.utcnow()
        )
        
        return await self.send_message(embeds=[embed])
    
    async def send_technician_notification(
        self,
        technician_name: str,
        notification_type: str,
        message: str
    ) -> bool:
        """
        Send technician-specific notification to Discord.
        
        Args:
            technician_name: Technician name
            notification_type: Type of notification
            message: Notification message
            
        Returns:
            True if sent successfully
        """
        embed = self.create_embed(
            title=f"👷 {technician_name} - {notification_type}",
            description=message,
            color=DiscordColor.INFO,
            footer="TradeSense Technician Updates",
            timestamp=datetime.utcnow()
        )
        
        return await self.send_message(embeds=[embed])
    
    def get_stats(self) -> dict:
        """
        Get Discord notification statistics.
        
        Returns:
            Dictionary with sent/failed counts
        """
        return {
            'sent': self.sent_count,
            'failed': self.failed_count,
            'success_rate': (
                self.sent_count / (self.sent_count + self.failed_count)
                if (self.sent_count + self.failed_count) > 0
                else 0.0
            )
        }


# Factory function
def create_discord_notifier(
    webhook_url: str,
    username: str = "TradeSense Bot",
    avatar_url: Optional[str] = None
) -> DiscordNotifier:
    """
    Factory function to create Discord notifier.
    
    Args:
        webhook_url: Discord webhook URL
        username: Bot username
        avatar_url: Bot avatar URL
        
    Returns:
        Configured DiscordNotifier instance
    """
    config = DiscordWebhookConfig(
        webhook_url=webhook_url,
        username=username,
        avatar_url=avatar_url
    )
    
    return DiscordNotifier(config)
