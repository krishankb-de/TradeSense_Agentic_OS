"""
Example script demonstrating Intake Agent notification integration
Shows lead creation and notification flow

Validates: Requirements 4.8, 4.10
"""

import asyncio
import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from agents.intake import (
    IntakeAgent,
    LeadInput,
    LeadSource,
    UrgencyLevel,
    CustomerInfo,
    create_intake_agent,
)
from llm.unified_client import create_unified_llm_client
from notifications import (
    create_email_notifier,
    create_web_push_notifier,
    create_discord_notifier,
)
from db.models import Technician
from uuid import uuid4
from datetime import datetime


async def main():
    """Demonstrate intake agent notification integration."""
    
    print("=" * 80)
    print("Intake Agent Notification Integration Example")
    print("=" * 80)
    print()
    
    # ========================================================================
    # Step 1: Initialize Services
    # ========================================================================
    
    print("Step 1: Initializing services...")
    print()
    
    # Create LLM client
    llm_client = create_unified_llm_client()
    print("✓ LLM client initialized")
    
    # Create notification services (mock for example)
    # In production, these would use real SMTP, VAPID, and Discord webhook
    email_notifier = None  # Would be: create_email_notifier(...)
    push_notifier = None   # Would be: create_web_push_notifier(...)
    discord_notifier = None  # Would be: create_discord_notifier(...)
    
    print("✓ Notification services initialized (mock)")
    
    # Create intake agent
    intake_agent = create_intake_agent(
        llm_client=llm_client,
        email_notifier=email_notifier,
        push_notifier=push_notifier,
        discord_notifier=discord_notifier,
    )
    print("✓ Intake agent initialized")
    print()
    
    # ========================================================================
    # Step 2: Capture Lead
    # ========================================================================
    
    print("Step 2: Capturing lead from voice call...")
    print()
    
    # Create lead input
    lead_input = LeadInput(
        source=LeadSource.VOICE,
        customer_info=CustomerInfo(
            name="John Smith",
            email="john@example.com",
            phone="555-1234",
            address="123 Main St, Springfield",
        ),
        issue_description="My furnace stopped working and it's freezing outside. No heat at all.",
        urgency=None,  # Will be classified by agent
        location=None,
        raw_text="My furnace stopped working and it's freezing outside. No heat at all.",
    )
    
    print(f"Customer: {lead_input.customer_info.name}")
    print(f"Issue: {lead_input.issue_description}")
    print(f"Source: {lead_input.source.value}")
    print()
    
    try:
        # Capture lead
        lead = await intake_agent.capture_lead(lead_input)
        print(f"✓ Lead captured: {lead.id}")
        print(f"  Customer ID: {lead.customer_id}")
        print(f"  Status: {lead.status}")
        print()
    except Exception as e:
        print(f"✗ Failed to capture lead: {e}")
        return
    
    # ========================================================================
    # Step 3: Triage Lead
    # ========================================================================
    
    print("Step 3: Triaging lead...")
    print()
    
    try:
        # Triage lead
        triage_result = await intake_agent.triage_lead(lead)
        
        print(f"✓ Lead triaged successfully")
        print(f"  Service Type: {triage_result.service_type}")
        print(f"  Urgency: {triage_result.urgency.value}")
        print(f"  Priority: {triage_result.priority}/10")
        print(f"  Confidence: {triage_result.confidence:.0%}")
        print(f"  Estimated Duration: {triage_result.estimated_duration} minutes")
        print(f"  Required Skills: {', '.join(triage_result.required_skills)}")
        print(f"  Reasoning: {triage_result.reasoning[:200]}...")
        print()
    except Exception as e:
        print(f"✗ Failed to triage lead: {e}")
        return
    
    # ========================================================================
    # Step 4: Send Notifications
    # ========================================================================
    
    print("Step 4: Sending notifications...")
    print()
    
    # Create mock technician
    technician = Technician(
        id=uuid4(),
        name="Mike Johnson",
        email="mike@tradesense.com",
        phone="555-5678",
        skills=["HVAC", "EPA 608 Certified"],
        status="available",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    # Notify technician
    print("Notifying technician...")
    tech_result = await intake_agent.notify_technician_assignment(
        lead, technician, triage_result
    )
    if tech_result:
        print(f"✓ Technician notification sent to {technician.name}")
    else:
        print(f"✗ Technician notification failed (notifier not configured)")
    print()
    
    # Notify customer
    print("Notifying customer...")
    customer_result = await intake_agent.notify_customer_confirmation(
        lead, technician, "Today at 3:00 PM"
    )
    if customer_result:
        print(f"✓ Customer confirmation sent to {lead.customer.email}")
    else:
        print(f"✗ Customer confirmation failed (notifier not configured)")
    print()
    
    # Notify team
    print("Notifying team...")
    team_result = await intake_agent.notify_team_new_lead(
        lead, triage_result
    )
    if team_result:
        print(f"✓ Team notification sent via Discord")
    else:
        print(f"✗ Team notification failed (notifier not configured)")
    print()
    
    # Send emergency alert if needed
    if lead.urgency == "emergency":
        print("Sending emergency alert...")
        emergency_result = await intake_agent.notify_emergency_alert(
            lead, triage_result
        )
        if emergency_result:
            print(f"✓ Emergency alert sent via Discord")
        else:
            print(f"✗ Emergency alert failed (notifier not configured)")
        print()
    
    # ========================================================================
    # Step 5: Summary
    # ========================================================================
    
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    
    print(f"Lead ID: {lead.id}")
    print(f"Customer: {lead.customer.name}")
    print(f"Service Type: {triage_result.service_type}")
    print(f"Urgency: {triage_result.urgency.value}")
    print(f"Priority: {triage_result.priority}/10")
    print(f"Assigned Technician: {technician.name}")
    print()
    
    # Count successful notifications
    notifications_sent = sum([
        tech_result,
        customer_result,
        team_result,
        emergency_result if lead.urgency == "emergency" else False
    ])
    total_notifications = 4 if lead.urgency == "emergency" else 3
    
    print(f"Notifications: {notifications_sent}/{total_notifications} sent")
    print()
    
    # Agent statistics
    stats = intake_agent.get_statistics()
    print("Agent Statistics:")
    print(f"  Total Leads: {stats['total_leads']}")
    print(f"  Successful Triages: {stats['successful_triages']}")
    print(f"  Failed Triages: {stats['failed_triages']}")
    print(f"  Success Rate: {stats['success_rate']:.1f}%")
    print()
    
    print("=" * 80)
    print("Example completed successfully!")
    print("=" * 80)
    print()
    
    # ========================================================================
    # Configuration Instructions
    # ========================================================================
    
    print("To enable real notifications, configure the following environment variables:")
    print()
    print("Email Notifications:")
    print("  SMTP_HOST=smtp.gmail.com")
    print("  SMTP_PORT=587")
    print("  SMTP_USERNAME=your-email@gmail.com")
    print("  SMTP_PASSWORD=your-app-password")
    print("  FROM_EMAIL=noreply@tradesense.com")
    print("  FROM_NAME=TradeSense")
    print()
    print("Web Push Notifications:")
    print("  VAPID_PRIVATE_KEY=your-vapid-private-key")
    print("  VAPID_PUBLIC_KEY=your-vapid-public-key")
    print("  VAPID_SUBJECT=mailto:admin@tradesense.com")
    print()
    print("Discord Notifications:")
    print("  DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
    print("  DISCORD_BOT_USERNAME=TradeSense Bot")
    print()


if __name__ == "__main__":
    asyncio.run(main())
