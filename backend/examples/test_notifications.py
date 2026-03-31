"""
Example: Notification System Integration
Demonstrates WebRTC signaling, email, web push, and Discord notifications
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv

from notifications import (
    create_webrtc_signaling_server,
    create_email_notifier,
    create_web_push_notifier,
    create_discord_notifier
)

# Load environment variables
load_dotenv()


async def test_webrtc_signaling():
    """Test WebRTC signaling server."""
    print("\n=== Testing WebRTC Signaling ===")
    
    # Create signaling server
    signaling = create_webrtc_signaling_server()
    
    # Set event handlers
    async def on_offer(msg):
        print(f"Received offer for session {msg.session_id}")
    
    async def on_answer(msg):
        print(f"Received answer for session {msg.session_id}")
    
    signaling.set_handlers(on_offer=on_offer, on_answer=on_answer)
    
    # Simulate WebRTC handshake
    session_id = "test-session-123"
    
    # 1. Client sends offer
    offer_response = await signaling.handle_message("peer-1", {
        'type': 'offer',
        'session_id': session_id,
        'payload': {
            'sdp': 'v=0\r\no=- 123456 2 IN IP4 127.0.0.1\r\n...'
        }
    })
    print(f"Offer response: {offer_response}")
    
    # 2. Server sends answer
    answer_response = await signaling.handle_message("peer-1", {
        'type': 'answer',
        'session_id': session_id,
        'payload': {
            'sdp': 'v=0\r\no=- 789012 2 IN IP4 127.0.0.1\r\n...'
        }
    })
    print(f"Answer response: {answer_response}")
    
    # 3. Exchange ICE candidates
    ice_response = await signaling.handle_message("peer-1", {
        'type': 'ice-candidate',
        'session_id': session_id,
        'payload': {
            'candidate': {
                'candidate': 'candidate:1 1 UDP 2130706431 192.168.1.1 54321 typ host',
                'sdpMLineIndex': 0,
                'sdpMid': 'audio'
            }
        }
    })
    print(f"ICE candidate response: {ice_response}")
    
    # Get session info
    session = signaling.get_session(session_id)
    print(f"Session state: {session['state']}")
    print(f"ICE candidates: {len(session['ice_candidates'])}")
    
    # Get active sessions
    active_sessions = signaling.get_active_sessions()
    print(f"Active sessions: {len(active_sessions)}")


async def test_email_notifications():
    """Test email notification system."""
    print("\n=== Testing Email Notifications ===")
    
    # Get configuration from environment
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_username = os.getenv('SMTP_USERNAME', 'your-email@gmail.com')
    smtp_password = os.getenv('SMTP_PASSWORD', 'your-app-password')
    from_email = os.getenv('FROM_EMAIL', 'noreply@tradesense.com')
    
    # Create email notifier
    email_notifier = create_email_notifier(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        from_email=from_email,
        from_name="TradeSense"
    )
    
    print(f"Email notifier configured: {smtp_host}:{smtp_port}")
    
    # Note: Uncomment to actually send emails (requires valid SMTP credentials)
    # 
    # # Send appointment confirmation
    # result = await email_notifier.send_appointment_confirmation(
    #     to_email="customer@example.com",
    #     customer_name="John Smith",
    #     appointment_time="Tomorrow at 2:00 PM",
    #     service_type="HVAC Repair",
    #     technician_name="Mike Johnson"
    # )
    # print(f"Appointment confirmation sent: {result}")
    # 
    # # Send technician arrival notification
    # result = await email_notifier.send_technician_arrival_notification(
    #     to_email="customer@example.com",
    #     customer_name="John Smith",
    #     technician_name="Mike Johnson",
    #     eta_minutes=15
    # )
    # print(f"Arrival notification sent: {result}")
    # 
    # # Send job completion notification
    # result = await email_notifier.send_job_completion_notification(
    #     to_email="customer@example.com",
    #     customer_name="John Smith",
    #     service_type="HVAC Repair",
    #     total_cost=285.00,
    #     parts_used=["Thermostat TH-2000", "Pressure Relief Valve PRV-200"],
    #     notes="Replaced faulty thermostat and installed new pressure relief valve."
    # )
    # print(f"Job completion notification sent: {result}")
    
    # Get statistics
    stats = email_notifier.get_stats()
    print(f"Email stats: {stats}")


async def test_web_push_notifications():
    """Test web push notification system."""
    print("\n=== Testing Web Push Notifications ===")
    
    # Create web push notifier
    push_notifier = create_web_push_notifier(
        vapid_private_key=os.getenv('VAPID_PRIVATE_KEY'),
        vapid_public_key=os.getenv('VAPID_PUBLIC_KEY'),
        vapid_subject=os.getenv('VAPID_SUBJECT', 'mailto:admin@tradesense.com')
    )
    
    # Add subscription
    subscription = push_notifier.add_subscription(
        user_id="tech-123",
        endpoint="https://fcm.googleapis.com/fcm/send/test-endpoint",
        keys={
            "p256dh": "test-p256dh-key",
            "auth": "test-auth-key"
        }
    )
    print(f"Added subscription for user: {subscription.user_id}")
    
    # Note: Uncomment to actually send push notifications (requires valid subscription)
    # 
    # # Send job assignment notification
    # result = await push_notifier.send_job_assignment_notification(
    #     user_id="tech-123",
    #     job_id="job-456",
    #     service_type="HVAC Repair",
    #     customer_name="John Smith",
    #     scheduled_time="2:00 PM"
    # )
    # print(f"Job assignment notification sent: {result}")
    # 
    # # Send emergency alert
    # result = await push_notifier.send_emergency_alert(
    #     user_id="tech-123",
    #     alert_message="Furnace failure in freezing weather",
    #     location="123 Main St, Springfield"
    # )
    # print(f"Emergency alert sent: {result}")
    # 
    # # Send schedule change notification
    # result = await push_notifier.send_schedule_change_notification(
    #     user_id="tech-123",
    #     change_type="added",
    #     details="New job added: HVAC Repair at 4:00 PM"
    # )
    # print(f"Schedule change notification sent: {result}")
    
    # Get statistics
    stats = push_notifier.get_stats()
    print(f"Push notification stats: {stats}")


async def test_discord_notifications():
    """Test Discord webhook notification system."""
    print("\n=== Testing Discord Notifications ===")
    
    # Get Discord webhook URL from environment
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    
    if not webhook_url:
        print("Discord webhook URL not configured (set DISCORD_WEBHOOK_URL)")
        return
    
    # Create Discord notifier
    discord_notifier = create_discord_notifier(
        webhook_url=webhook_url,
        username="TradeSense Bot"
    )
    
    # Note: Uncomment to actually send Discord notifications
    # 
    # # Send new lead alert
    # result = await discord_notifier.send_new_lead_alert(
    #     lead_id="lead-789",
    #     customer_name="John Smith",
    #     service_type="HVAC Repair",
    #     urgency="emergency",
    #     description="Furnace stopped working in freezing weather",
    #     location="123 Main St, Springfield"
    # )
    # print(f"New lead alert sent: {result}")
    # 
    # # Send emergency job alert
    # result = await discord_notifier.send_emergency_job_alert(
    #     job_id="job-456",
    #     customer_name="John Smith",
    #     service_type="HVAC Repair",
    #     location="123 Main St, Springfield",
    #     assigned_technician="Mike Johnson"
    # )
    # print(f"Emergency job alert sent: {result}")
    # 
    # # Send daily summary
    # result = await discord_notifier.send_daily_summary(
    #     date="2024-01-15",
    #     total_jobs=25,
    #     completed_jobs=23,
    #     revenue=5750.00,
    #     technician_utilization=0.85,
    #     first_time_fix_rate=0.92
    # )
    # print(f"Daily summary sent: {result}")
    # 
    # # Send system status
    # result = await discord_notifier.send_system_status(
    #     status="info",
    #     message="System running normally",
    #     details={
    #         "cpu_usage": "45%",
    #         "memory_usage": "62%",
    #         "active_sessions": 12
    #     }
    # )
    # print(f"System status sent: {result}")
    
    # Get statistics
    stats = discord_notifier.get_stats()
    print(f"Discord notification stats: {stats}")


async def test_integrated_workflow():
    """Test integrated notification workflow."""
    print("\n=== Testing Integrated Workflow ===")
    
    # Simulate a complete customer interaction workflow
    
    # 1. Customer initiates WebRTC call
    print("\n1. Customer initiates WebRTC call")
    signaling = create_webrtc_signaling_server()
    
    session_id = "customer-session-456"
    await signaling.handle_message("customer-peer", {
        'type': 'offer',
        'session_id': session_id,
        'payload': {'sdp': 'customer-offer-sdp'}
    })
    print(f"   WebRTC session established: {session_id}")
    
    # 2. Lead captured and triaged
    print("\n2. Lead captured and triaged")
    lead_data = {
        'lead_id': 'lead-789',
        'customer_name': 'John Smith',
        'customer_email': 'john.smith@example.com',
        'service_type': 'HVAC Repair',
        'urgency': 'emergency',
        'description': 'Furnace stopped working',
        'location': '123 Main St, Springfield'
    }
    print(f"   Lead created: {lead_data['lead_id']}")
    
    # 3. Send Discord alert to team
    print("\n3. Sending Discord alert to team")
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if webhook_url:
        discord_notifier = create_discord_notifier(webhook_url=webhook_url)
        # await discord_notifier.send_new_lead_alert(**lead_data)
        print("   Discord alert sent (commented out)")
    else:
        print("   Discord webhook not configured")
    
    # 4. Assign technician and send push notification
    print("\n4. Assigning technician and sending push notification")
    push_notifier = create_web_push_notifier()
    push_notifier.add_subscription(
        user_id="tech-123",
        endpoint="https://fcm.googleapis.com/fcm/send/tech-endpoint",
        keys={"p256dh": "key1", "auth": "key2"}
    )
    # await push_notifier.send_job_assignment_notification(
    #     user_id="tech-123",
    #     job_id="job-456",
    #     service_type=lead_data['service_type'],
    #     customer_name=lead_data['customer_name'],
    #     scheduled_time="ASAP"
    # )
    print("   Push notification sent (commented out)")
    
    # 5. Send email confirmation to customer
    print("\n5. Sending email confirmation to customer")
    # email_notifier = create_email_notifier(...)
    # await email_notifier.send_appointment_confirmation(
    #     to_email=lead_data['customer_email'],
    #     customer_name=lead_data['customer_name'],
    #     appointment_time="Within 2 hours",
    #     service_type=lead_data['service_type'],
    #     technician_name="Mike Johnson"
    # )
    print("   Email confirmation sent (commented out)")
    
    print("\n✅ Integrated workflow complete!")


async def main():
    """Run all notification tests."""
    print("=" * 60)
    print("TradeSense Notification System Test")
    print("=" * 60)
    
    try:
        # Test individual components
        await test_webrtc_signaling()
        await test_email_notifications()
        await test_web_push_notifications()
        await test_discord_notifications()
        
        # Test integrated workflow
        await test_integrated_workflow()
        
        print("\n" + "=" * 60)
        print("All tests completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
