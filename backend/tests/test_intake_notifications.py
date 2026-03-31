"""
Unit tests for Intake Agent notification integration
Tests lead creation and notification logic

Validates: Requirements 4.8, 4.10
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from agents.intake import (
    IntakeAgent,
    LeadInput,
    LeadSource,
    UrgencyLevel,
    CustomerInfo,
    TriageResult,
    create_intake_agent,
)
from llm.unified_client import UnifiedLLMClient
from llm.base import LLMResponse
from db.models import Lead, Customer, Technician
from notifications import EmailNotifier, WebPushNotifier, DiscordNotifier


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = Mock(spec=UnifiedLLMClient)
    client.generate = Mock(return_value=LLMResponse(
        text="Service type: HVAC, Urgency: emergency",
        model="gemini-pro",
        tokens_used=50,
        latency_ms=200,
    ))
    return client


@pytest.fixture
def mock_email_notifier():
    """Mock email notifier."""
    notifier = Mock(spec=EmailNotifier)
    notifier.send_appointment_confirmation = AsyncMock(return_value=True)
    return notifier


@pytest.fixture
def mock_push_notifier():
    """Mock web push notifier."""
    notifier = Mock(spec=WebPushNotifier)
    notifier.send_job_assignment_notification = AsyncMock(return_value=True)
    return notifier


@pytest.fixture
def mock_discord_notifier():
    """Mock Discord notifier."""
    notifier = Mock(spec=DiscordNotifier)
    notifier.send_new_lead_alert = AsyncMock(return_value=True)
    notifier.send_emergency_job_alert = AsyncMock(return_value=True)
    return notifier


@pytest.fixture
def intake_agent(mock_llm_client, mock_email_notifier, mock_push_notifier, mock_discord_notifier):
    """Create intake agent with mock notification services."""
    return IntakeAgent(
        llm_client=mock_llm_client,
        email_notifier=mock_email_notifier,
        push_notifier=mock_push_notifier,
        discord_notifier=mock_discord_notifier,
    )


@pytest.fixture
def sample_lead():
    """Sample lead object."""
    customer = Customer(
        id=uuid4(),
        name="John Smith",
        email="john@example.com",
        phone="555-1234",
        address="123 Main St",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    
    lead = Lead(
        id=uuid4(),
        customer_id=customer.id,
        source="voice",
        urgency="emergency",
        service_type="HVAC",
        description="Furnace stopped working",
        confidence_score=0.9,
        status="triaged",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    lead.customer = customer
    
    return lead


@pytest.fixture
def sample_technician():
    """Sample technician object."""
    return Technician(
        id=uuid4(),
        name="Mike Johnson",
        email="mike@tradesense.com",
        phone="555-5678",
        skills=["HVAC", "EPA 608 Certified"],
        status="available",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_triage_result():
    """Sample triage result."""
    return TriageResult(
        service_type="HVAC",
        estimated_duration=120,
        required_skills=["HVAC", "EPA 608 Certified"],
        suggested_technicians=[],
        priority=10,
        confidence=0.9,
        urgency=UrgencyLevel.EMERGENCY,
        reasoning="Emergency HVAC repair needed",
    )


# ============================================================================
# Test Notification Methods
# ============================================================================

@pytest.mark.asyncio
async def test_notify_technician_assignment(
    intake_agent,
    sample_lead,
    sample_technician,
    sample_triage_result,
    mock_push_notifier
):
    """Test technician notification via push."""
    # Notify technician
    result = await intake_agent.notify_technician_assignment(
        sample_lead,
        sample_technician,
        sample_triage_result
    )
    
    # Verify notification sent
    assert result is True
    mock_push_notifier.send_job_assignment_notification.assert_called_once()
    
    # Verify call arguments
    call_args = mock_push_notifier.send_job_assignment_notification.call_args
    assert call_args[1]["user_id"] == str(sample_technician.id)
    assert call_args[1]["job_id"] == str(sample_lead.id)
    assert call_args[1]["service_type"] == "HVAC"
    assert call_args[1]["customer_name"] == "John Smith"


@pytest.mark.asyncio
async def test_notify_technician_assignment_no_notifier(
    mock_llm_client,
    sample_lead,
    sample_technician,
    sample_triage_result
):
    """Test technician notification without push notifier configured."""
    # Create agent without push notifier
    agent = IntakeAgent(llm_client=mock_llm_client)
    
    # Notify technician
    result = await agent.notify_technician_assignment(
        sample_lead,
        sample_technician,
        sample_triage_result
    )
    
    # Should return False when notifier not configured
    assert result is False


@pytest.mark.asyncio
async def test_notify_customer_confirmation(
    intake_agent,
    sample_lead,
    sample_technician,
    mock_email_notifier
):
    """Test customer confirmation email."""
    # Notify customer
    result = await intake_agent.notify_customer_confirmation(
        sample_lead,
        sample_technician,
        "Tomorrow at 2:00 PM"
    )
    
    # Verify notification sent
    assert result is True
    mock_email_notifier.send_appointment_confirmation.assert_called_once()
    
    # Verify call arguments
    call_args = mock_email_notifier.send_appointment_confirmation.call_args
    assert call_args[1]["to_email"] == "john@example.com"
    assert call_args[1]["customer_name"] == "John Smith"
    assert call_args[1]["appointment_time"] == "Tomorrow at 2:00 PM"
    assert call_args[1]["service_type"] == "HVAC"
    assert call_args[1]["technician_name"] == "Mike Johnson"


@pytest.mark.asyncio
async def test_notify_customer_confirmation_no_email(
    intake_agent,
    sample_lead,
    sample_technician
):
    """Test customer notification when customer has no email."""
    # Remove customer email
    sample_lead.customer.email = None
    
    # Notify customer
    result = await intake_agent.notify_customer_confirmation(
        sample_lead,
        sample_technician
    )
    
    # Should return False when no email
    assert result is False


@pytest.mark.asyncio
async def test_notify_team_new_lead(
    intake_agent,
    sample_lead,
    sample_triage_result,
    mock_discord_notifier
):
    """Test team notification via Discord."""
    # Notify team
    result = await intake_agent.notify_team_new_lead(
        sample_lead,
        sample_triage_result
    )
    
    # Verify notification sent
    assert result is True
    mock_discord_notifier.send_new_lead_alert.assert_called_once()
    
    # Verify call arguments
    call_args = mock_discord_notifier.send_new_lead_alert.call_args
    assert call_args[1]["lead_id"] == str(sample_lead.id)
    assert call_args[1]["customer_name"] == "John Smith"
    assert call_args[1]["service_type"] == "HVAC"
    assert call_args[1]["urgency"] == "emergency"


@pytest.mark.asyncio
async def test_notify_emergency_alert(
    intake_agent,
    sample_lead,
    sample_triage_result,
    mock_discord_notifier
):
    """Test emergency alert via Discord."""
    # Notify emergency
    result = await intake_agent.notify_emergency_alert(
        sample_lead,
        sample_triage_result
    )
    
    # Verify notification sent
    assert result is True
    mock_discord_notifier.send_emergency_job_alert.assert_called_once()
    
    # Verify call arguments
    call_args = mock_discord_notifier.send_emergency_job_alert.call_args
    assert call_args[1]["job_id"] == str(sample_lead.id)
    assert call_args[1]["customer_name"] == "John Smith"
    assert call_args[1]["service_type"] == "HVAC"


@pytest.mark.asyncio
async def test_notify_emergency_alert_non_emergency(
    intake_agent,
    sample_lead,
    sample_triage_result,
    mock_discord_notifier
):
    """Test emergency alert skipped for non-emergency leads."""
    # Change to non-emergency
    sample_lead.urgency = "routine"
    
    # Notify emergency
    result = await intake_agent.notify_emergency_alert(
        sample_lead,
        sample_triage_result
    )
    
    # Should return False for non-emergency
    assert result is False
    mock_discord_notifier.send_emergency_job_alert.assert_not_called()


# ============================================================================
# Test Notification Error Handling
# ============================================================================

@pytest.mark.asyncio
async def test_notify_technician_assignment_error(
    intake_agent,
    sample_lead,
    sample_technician,
    sample_triage_result,
    mock_push_notifier
):
    """Test technician notification error handling."""
    # Configure mock to raise exception
    mock_push_notifier.send_job_assignment_notification.side_effect = Exception("Network error")
    
    # Notify technician
    result = await intake_agent.notify_technician_assignment(
        sample_lead,
        sample_technician,
        sample_triage_result
    )
    
    # Should return False on error
    assert result is False


@pytest.mark.asyncio
async def test_notify_customer_confirmation_error(
    intake_agent,
    sample_lead,
    sample_technician,
    mock_email_notifier
):
    """Test customer notification error handling."""
    # Configure mock to raise exception
    mock_email_notifier.send_appointment_confirmation.side_effect = Exception("SMTP error")
    
    # Notify customer
    result = await intake_agent.notify_customer_confirmation(
        sample_lead,
        sample_technician
    )
    
    # Should return False on error
    assert result is False


@pytest.mark.asyncio
async def test_notify_team_new_lead_error(
    intake_agent,
    sample_lead,
    sample_triage_result,
    mock_discord_notifier
):
    """Test team notification error handling."""
    # Configure mock to raise exception
    mock_discord_notifier.send_new_lead_alert.side_effect = Exception("Webhook error")
    
    # Notify team
    result = await intake_agent.notify_team_new_lead(
        sample_lead,
        sample_triage_result
    )
    
    # Should return False on error
    assert result is False


# ============================================================================
# Test Factory Function
# ============================================================================

def test_create_intake_agent_with_notifications(
    mock_llm_client,
    mock_email_notifier,
    mock_push_notifier,
    mock_discord_notifier
):
    """Test factory function with notification services."""
    agent = create_intake_agent(
        llm_client=mock_llm_client,
        email_notifier=mock_email_notifier,
        push_notifier=mock_push_notifier,
        discord_notifier=mock_discord_notifier,
    )
    
    assert agent is not None
    assert agent.llm_client == mock_llm_client
    assert agent.email_notifier == mock_email_notifier
    assert agent.push_notifier == mock_push_notifier
    assert agent.discord_notifier == mock_discord_notifier


def test_create_intake_agent_without_notifications(mock_llm_client):
    """Test factory function without notification services."""
    agent = create_intake_agent(llm_client=mock_llm_client)
    
    assert agent is not None
    assert agent.llm_client == mock_llm_client
    assert agent.email_notifier is None
    assert agent.push_notifier is None
    assert agent.discord_notifier is None


# ============================================================================
# Test Integration Scenarios
# ============================================================================

@pytest.mark.asyncio
async def test_complete_notification_flow(
    intake_agent,
    sample_lead,
    sample_technician,
    sample_triage_result,
    mock_email_notifier,
    mock_push_notifier,
    mock_discord_notifier
):
    """Test complete notification flow for emergency lead."""
    # Send all notifications
    tech_result = await intake_agent.notify_technician_assignment(
        sample_lead, sample_technician, sample_triage_result
    )
    customer_result = await intake_agent.notify_customer_confirmation(
        sample_lead, sample_technician
    )
    team_result = await intake_agent.notify_team_new_lead(
        sample_lead, sample_triage_result
    )
    emergency_result = await intake_agent.notify_emergency_alert(
        sample_lead, sample_triage_result
    )
    
    # Verify all notifications sent
    assert tech_result is True
    assert customer_result is True
    assert team_result is True
    assert emergency_result is True
    
    # Verify all notifiers called
    mock_push_notifier.send_job_assignment_notification.assert_called_once()
    mock_email_notifier.send_appointment_confirmation.assert_called_once()
    mock_discord_notifier.send_new_lead_alert.assert_called_once()
    mock_discord_notifier.send_emergency_job_alert.assert_called_once()


@pytest.mark.asyncio
async def test_partial_notification_failure(
    intake_agent,
    sample_lead,
    sample_technician,
    sample_triage_result,
    mock_email_notifier,
    mock_push_notifier,
    mock_discord_notifier
):
    """Test handling of partial notification failures."""
    # Configure one notifier to fail
    mock_email_notifier.send_appointment_confirmation.side_effect = Exception("SMTP error")
    
    # Send all notifications
    tech_result = await intake_agent.notify_technician_assignment(
        sample_lead, sample_technician, sample_triage_result
    )
    customer_result = await intake_agent.notify_customer_confirmation(
        sample_lead, sample_technician
    )
    team_result = await intake_agent.notify_team_new_lead(
        sample_lead, sample_triage_result
    )
    
    # Verify partial success
    assert tech_result is True
    assert customer_result is False  # Failed
    assert team_result is True
    
    # Verify successful notifiers still called
    mock_push_notifier.send_job_assignment_notification.assert_called_once()
    mock_discord_notifier.send_new_lead_alert.assert_called_once()


# ============================================================================
# Test Notification Content
# ============================================================================

@pytest.mark.asyncio
async def test_technician_notification_content(
    intake_agent,
    sample_lead,
    sample_technician,
    sample_triage_result,
    mock_push_notifier
):
    """Test technician notification contains correct information."""
    await intake_agent.notify_technician_assignment(
        sample_lead,
        sample_technician,
        sample_triage_result
    )
    
    # Get call arguments
    call_args = mock_push_notifier.send_job_assignment_notification.call_args[1]
    
    # Verify content
    assert call_args["user_id"] == str(sample_technician.id)
    assert call_args["job_id"] == str(sample_lead.id)
    assert call_args["service_type"] == sample_triage_result.service_type
    assert call_args["customer_name"] == sample_lead.customer.name
    assert "ASAP" in call_args["scheduled_time"]  # Emergency lead


@pytest.mark.asyncio
async def test_customer_notification_content(
    intake_agent,
    sample_lead,
    sample_technician,
    mock_email_notifier
):
    """Test customer notification contains correct information."""
    appointment_time = "Tomorrow at 2:00 PM"
    
    await intake_agent.notify_customer_confirmation(
        sample_lead,
        sample_technician,
        appointment_time
    )
    
    # Get call arguments
    call_args = mock_email_notifier.send_appointment_confirmation.call_args[1]
    
    # Verify content
    assert call_args["to_email"] == sample_lead.customer.email
    assert call_args["customer_name"] == sample_lead.customer.name
    assert call_args["appointment_time"] == appointment_time
    assert call_args["service_type"] == sample_lead.service_type
    assert call_args["technician_name"] == sample_technician.name


@pytest.mark.asyncio
async def test_team_notification_content(
    intake_agent,
    sample_lead,
    sample_triage_result,
    mock_discord_notifier
):
    """Test team notification contains correct information."""
    await intake_agent.notify_team_new_lead(
        sample_lead,
        sample_triage_result
    )
    
    # Get call arguments
    call_args = mock_discord_notifier.send_new_lead_alert.call_args[1]
    
    # Verify content
    assert call_args["lead_id"] == str(sample_lead.id)
    assert call_args["customer_name"] == sample_lead.customer.name
    assert call_args["service_type"] == sample_triage_result.service_type
    assert call_args["urgency"] == sample_lead.urgency
    assert call_args["description"] == sample_lead.description
    assert call_args["location"] == sample_lead.customer.address


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
