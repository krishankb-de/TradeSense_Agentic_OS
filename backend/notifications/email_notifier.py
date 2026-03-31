"""
Email Notification System
Handles SMTP-based email notifications for customer updates
Validates: Requirements 4.8, 4.9
"""

import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email server configuration."""
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    from_email: str
    from_name: str = "TradeSense"
    use_tls: bool = True
    use_ssl: bool = False


class EmailNotifier:
    """
    Email Notification System.
    
    Sends email notifications to customers for:
    - Appointment confirmations
    - Technician arrival notifications
    - Job completion updates
    - Invoice delivery
    
    Features:
    - Async SMTP client
    - HTML and plain text support
    - Template-based emails
    - Delivery tracking
    
    Validates: Requirements 4.8, 4.9
    """
    
    def __init__(self, config: EmailConfig):
        """
        Initialize email notifier.
        
        Args:
            config: Email server configuration
        """
        self.config = config
        self.sent_count = 0
        self.failed_count = 0
        
        logger.info(
            f"Email notifier initialized: {config.smtp_host}:{config.smtp_port}"
        )
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Send email notification.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_text: Plain text body
            body_html: Optional HTML body
            cc: Optional CC recipients
            bcc: Optional BCC recipients
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = f"{self.config.from_name} <{self.config.from_email}>"
            message['To'] = to_email
            message['Subject'] = subject
            message['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
            
            if cc:
                message['Cc'] = ', '.join(cc)
            if bcc:
                message['Bcc'] = ', '.join(bcc)
            
            # Attach plain text
            text_part = MIMEText(body_text, 'plain', 'utf-8')
            message.attach(text_part)
            
            # Attach HTML if provided
            if body_html:
                html_part = MIMEText(body_html, 'html', 'utf-8')
                message.attach(html_part)
            
            # Send email
            await self._send_smtp(message, to_email, cc, bcc)
            
            self.sent_count += 1
            logger.info(f"Email sent to {to_email}: {subject}")
            
            return True
            
        except Exception as e:
            self.failed_count += 1
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def _send_smtp(
        self,
        message: MIMEMultipart,
        to_email: str,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ):
        """
        Send email via SMTP.
        
        Args:
            message: Email message
            to_email: Primary recipient
            cc: CC recipients
            bcc: BCC recipients
        """
        # Build recipient list
        recipients = [to_email]
        if cc:
            recipients.extend(cc)
        if bcc:
            recipients.extend(bcc)
        
        # Connect and send
        if self.config.use_ssl:
            # Use SMTP_SSL for port 465
            async with aiosmtplib.SMTP(
                hostname=self.config.smtp_host,
                port=self.config.smtp_port,
                use_tls=True
            ) as smtp:
                await smtp.login(
                    self.config.smtp_username,
                    self.config.smtp_password
                )
                await smtp.send_message(message, recipients=recipients)
        else:
            # Use STARTTLS for port 587
            async with aiosmtplib.SMTP(
                hostname=self.config.smtp_host,
                port=self.config.smtp_port
            ) as smtp:
                if self.config.use_tls:
                    await smtp.starttls()
                await smtp.login(
                    self.config.smtp_username,
                    self.config.smtp_password
                )
                await smtp.send_message(message, recipients=recipients)
    
    async def send_appointment_confirmation(
        self,
        to_email: str,
        customer_name: str,
        appointment_time: str,
        service_type: str,
        technician_name: str
    ) -> bool:
        """
        Send appointment confirmation email.
        
        Args:
            to_email: Customer email
            customer_name: Customer name
            appointment_time: Appointment time string
            service_type: Type of service
            technician_name: Assigned technician name
            
        Returns:
            True if sent successfully
        """
        subject = f"Appointment Confirmed - {service_type}"
        
        body_text = f"""
Hello {customer_name},

Your service appointment has been confirmed!

Service Type: {service_type}
Scheduled Time: {appointment_time}
Technician: {technician_name}

Your technician will call 30 minutes before arrival.

If you need to reschedule, please contact us as soon as possible.

Thank you for choosing TradeSense!

---
TradeSense Field Service Management
"""
        
        body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c3e50;">Appointment Confirmed</h2>
    
    <p>Hello {customer_name},</p>
    
    <p>Your service appointment has been confirmed!</p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <p style="margin: 5px 0;"><strong>Service Type:</strong> {service_type}</p>
        <p style="margin: 5px 0;"><strong>Scheduled Time:</strong> {appointment_time}</p>
        <p style="margin: 5px 0;"><strong>Technician:</strong> {technician_name}</p>
    </div>
    
    <p>Your technician will call 30 minutes before arrival.</p>
    
    <p>If you need to reschedule, please contact us as soon as possible.</p>
    
    <p>Thank you for choosing TradeSense!</p>
    
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="font-size: 12px; color: #666;">
        TradeSense Field Service Management
    </p>
</body>
</html>
"""
        
        return await self.send_email(to_email, subject, body_text, body_html)
    
    async def send_technician_arrival_notification(
        self,
        to_email: str,
        customer_name: str,
        technician_name: str,
        eta_minutes: int
    ) -> bool:
        """
        Send technician arrival notification.
        
        Args:
            to_email: Customer email
            customer_name: Customer name
            technician_name: Technician name
            eta_minutes: Estimated arrival time in minutes
            
        Returns:
            True if sent successfully
        """
        subject = f"Technician Arriving Soon - {eta_minutes} minutes"
        
        body_text = f"""
Hello {customer_name},

Your technician {technician_name} is on the way!

Estimated arrival: {eta_minutes} minutes

Please ensure someone is available to provide access to the service area.

Thank you!

---
TradeSense Field Service Management
"""
        
        body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c3e50;">Technician Arriving Soon</h2>
    
    <p>Hello {customer_name},</p>
    
    <p>Your technician <strong>{technician_name}</strong> is on the way!</p>
    
    <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #4caf50;">
        <p style="margin: 0; font-size: 18px;"><strong>Estimated arrival: {eta_minutes} minutes</strong></p>
    </div>
    
    <p>Please ensure someone is available to provide access to the service area.</p>
    
    <p>Thank you!</p>
    
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="font-size: 12px; color: #666;">
        TradeSense Field Service Management
    </p>
</body>
</html>
"""
        
        return await self.send_email(to_email, subject, body_text, body_html)
    
    async def send_job_completion_notification(
        self,
        to_email: str,
        customer_name: str,
        service_type: str,
        total_cost: float,
        parts_used: List[str],
        notes: str
    ) -> bool:
        """
        Send job completion notification.
        
        Args:
            to_email: Customer email
            customer_name: Customer name
            service_type: Type of service completed
            total_cost: Total job cost
            parts_used: List of parts used
            notes: Technician notes
            
        Returns:
            True if sent successfully
        """
        subject = f"Service Completed - {service_type}"
        
        parts_list = '\n'.join([f"- {part}" for part in parts_used])
        
        body_text = f"""
Hello {customer_name},

Your service has been completed!

Service Type: {service_type}
Total Cost: ${total_cost:.2f}

Parts Used:
{parts_list}

Technician Notes:
{notes}

An invoice will be sent separately.

Thank you for choosing TradeSense!

---
TradeSense Field Service Management
"""
        
        parts_html = ''.join([f"<li>{part}</li>" for part in parts_used])
        
        body_html = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <h2 style="color: #2c3e50;">Service Completed</h2>
    
    <p>Hello {customer_name},</p>
    
    <p>Your service has been completed!</p>
    
    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <p style="margin: 5px 0;"><strong>Service Type:</strong> {service_type}</p>
        <p style="margin: 5px 0;"><strong>Total Cost:</strong> ${total_cost:.2f}</p>
    </div>
    
    <h3 style="color: #2c3e50;">Parts Used:</h3>
    <ul>
        {parts_html}
    </ul>
    
    <h3 style="color: #2c3e50;">Technician Notes:</h3>
    <p style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">{notes}</p>
    
    <p>An invoice will be sent separately.</p>
    
    <p>Thank you for choosing TradeSense!</p>
    
    <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
    <p style="font-size: 12px; color: #666;">
        TradeSense Field Service Management
    </p>
</body>
</html>
"""
        
        return await self.send_email(to_email, subject, body_text, body_html)
    
    def get_stats(self) -> dict:
        """
        Get email notification statistics.
        
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
def create_email_notifier(
    smtp_host: str,
    smtp_port: int,
    smtp_username: str,
    smtp_password: str,
    from_email: str,
    from_name: str = "TradeSense",
    use_tls: bool = True,
    use_ssl: bool = False
) -> EmailNotifier:
    """
    Factory function to create email notifier.
    
    Args:
        smtp_host: SMTP server hostname
        smtp_port: SMTP server port
        smtp_username: SMTP username
        smtp_password: SMTP password
        from_email: Sender email address
        from_name: Sender display name
        use_tls: Use STARTTLS
        use_ssl: Use SSL/TLS
        
    Returns:
        Configured EmailNotifier instance
    """
    config = EmailConfig(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        from_email=from_email,
        from_name=from_name,
        use_tls=use_tls,
        use_ssl=use_ssl
    )
    
    return EmailNotifier(config)
