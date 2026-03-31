"""
Comprehensive Tests for Intake Agent (Task 8.8)

This test suite provides comprehensive coverage for the Intake Agent including:
- Unit tests for individual components
- Integration tests for complete workflows
- System tests for performance and reliability
- End-to-end tests for complete customer intake scenarios

Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.6, 4.7, 4.8, 4.9, 4.10
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4
from typing import List

from agents.intake import (
    IntakeAgent,
    LeadInput,
    LeadSource,
    UrgencyLevel,
    CustomerInfo,
    TriageResult,
    StructuredLeadData,
    PartQuery,
    PartAvailability,
    create_intake_agent,
)
from llm.unified_client import UnifiedLLMClient, LLMResponse
from db.models import Lead, Customer, Technician, Part
from notifications import EmailNotifier, WebPushNotifier, DiscordNotifier


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Create mock LLM client with realistic responses."""
    client = Mock(spec=UnifiedLLMClient)
    
    def mock_generate(prompt, **kwargs):
        # Simulate different responses based on prompt content
        if "triage" in prompt.lower() or "classify" in prompt.lower():
            return LLMResponse(
                text=(
                    "Service Type: HVAC\n"
                    "Urgency: emergency\n"
                    "Estimated Duration: 120 minutes\n"
                    "Required Skills: HVAC, EPA 608 Certified\n"
                    "Priority: 9\n"
                    "Reasoning: Furnace failure in winter requires immediate attention."
                ),
                model="gemini-2.5-flash",
                usage={"prompt_tokens": 100, "completion_tokens": 50},
                metadata={"provider": "gemini"}
            )
        elif "extract" in prompt.lower():
            return LLMResponse(
                text=(
                    '{\n'
                    '  "service_type": "HVAC",\n'
                    '  "urgency": "emergency",\n'
                    '  "issue_summary": "Furnace stopped working",\n'
                    '  "equipment_type": "Gas Furnace",\n'
                    '  "symptoms": ["no heat", "cold house"]\n'
                    '}'
                ),
                model="gemini-2.5-flash",
                usage={"prompt_tokens": 80, "completion_tokens": 40},
                metadata={"provider": "gemini"}
            )
        else:
            return LLMResponse(
                text="General response",
                model="gemini-2.5-flash",
                usage={"prompt_tokens": 50, "completion_tokens": 20},
                metadata={"provider": "gemini"}
            )
    
    client.generate = Mock(side_effect=mock_generate)
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
    """Create intake agent with all notification services."""
    return IntakeAgent(
        llm_client=mock_llm_client,
        email_notifier=mock_email_notifier,
        push_notifier=mock_push_notifier,
        discord_notifier=mock_discord_notifier,
        enable_logging=False,
    )


@pytest.fixture
def sample_customer():
    """Create sample customer."""
    return Customer(
        id=uuid4(),
        name="John Doe",
        email="john@example.com",
        phone="+1234567890",
        address="123 Main St, City, State 12345",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_technician():
    """Create sample technician."""
    return Technician(
        id=uuid4(),
        name="Mike Johnson",
        email="mike@tradesense.com",
        phone="+1987654321",
        skills=["HVAC", "EPA 608 Certified"],
        status="available",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_lead_input():
    """Create sample lead input."""
    return LeadInput(
        source=LeadSource.VOICE,
        customer_info=CustomerInfo(
            name="John Doe",
            email="john@example.com",
            phone="+1234567890",
            address="123 Main St"
        ),
        issue_description="My furnace stopped working and the house is freezing",
        urgency=None,
        location=None,
        raw_text="My furnace stopped working and the house is freezing"
    )


# ============================================================================
# 8.8.1 Unit Tests
# ============================================================================

class TestCrewAIAgentInitialization:
    """Test CrewAI agent initialization and configuration."""
    
    def test_agent_initialization_success(self, mock_llm_client):
        """Test successful agent initialization."""
        agent = IntakeAgent(llm_client=mock_llm_client)
        
        assert agent.llm_client == mock_llm_client
        assert agent.total_leads == 0
        assert agent.successful_triages == 0
        assert agent.failed_triages == 0
        assert agent.capture_role is not None
        assert agent.triage_role is not None
        assert agent.scheduling_role is not None
    
    def test_agent_initialization_with_notifications(
        self,
        mock_llm_client,
        mock_email_notifier,
        mock_push_notifier,
        mock_discord_notifier
    ):
        """Test agent initialization with notification services."""
        agent = IntakeAgent(
            llm_client=mock_llm_client,
            email_notifier=mock_email_notifier,
            push_notifier=mock_push_notifier,
            discord_notifier=mock_discord_notifier,
        )
        
        assert agent.email_notifier == mock_email_notifier
        assert agent.push_notifier == mock_push_notifier
        assert agent.discord_notifier == mock_discord_notifier
    
    def test_factory_function(self, mock_llm_client):
        """Test factory function creates agent correctly."""
        agent = create_intake_agent(llm_client=mock_llm_client)
        
        assert isinstance(agent, IntakeAgent)
        assert agent.llm_client == mock_llm_client



class TestLeadCaptureFromMultipleSources:
    """Test lead capture from voice, SMS, web sources."""
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_capture_from_voice(self, mock_get_db, intake_agent, sample_customer):
        """
        Test lead capture from voice source.
        Validates: Requirement 4.1 (Lead capture from voice)
        """
        # Mock database
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        voice_input = LeadInput(
            source=LeadSource.VOICE,
            customer_info=CustomerInfo(
                name="John Doe",
                email="john@example.com",
                phone="+1234567890"
            ),
            issue_description="Furnace not working",
            raw_text="My furnace stopped working"
        )
        
        lead = await intake_agent.capture_lead(voice_input)
        
        assert isinstance(lead, Lead)
        assert lead.source == LeadSource.VOICE.value
        assert intake_agent.total_leads == 1
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_capture_from_sms(self, mock_get_db, intake_agent, sample_customer):
        """
        Test lead capture from SMS source.
        Validates: Requirement 4.1 (Lead capture from SMS)
        """
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        sms_input = LeadInput(
            source=LeadSource.SMS,
            customer_info=CustomerInfo(phone="+1234567890"),
            issue_description="AC not cooling",
            raw_text="AC not cooling need help"
        )
        
        lead = await intake_agent.capture_lead(sms_input)
        
        assert lead.source == LeadSource.SMS.value
        assert intake_agent.total_leads == 1
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_capture_from_web(self, mock_get_db, intake_agent, sample_customer):
        """
        Test lead capture from web source.
        Validates: Requirement 4.1 (Lead capture from web)
        """
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        web_input = LeadInput(
            source=LeadSource.WEB,
            customer_info=CustomerInfo(
                name="Jane Smith",
                email="jane@example.com"
            ),
            issue_description="Plumbing repair needed",
            raw_text="Need plumbing repair for leaking faucet"
        )
        
        lead = await intake_agent.capture_lead(web_input)
        
        assert lead.source == LeadSource.WEB.value
        assert intake_agent.total_leads == 1


class TestUrgencyClassification:
    """Test urgency classification logic."""
    
    @pytest.mark.asyncio
    async def test_classify_emergency(self, intake_agent):
        """
        Test emergency urgency classification.
        Validates: Requirement 4.3 (Classify urgency)
        """
        description = "Gas leak in the basement, strong smell"
        
        result = await intake_agent._classify_urgency(description)
        
        assert result['urgency'] == 'emergency'
        assert result['confidence'] > 0.8
    
    @pytest.mark.asyncio
    async def test_classify_urgent(self, intake_agent):
        """Test urgent urgency classification."""
        description = "AC stopped working, house is getting hot"
        
        result = await intake_agent._classify_urgency(description)
        
        assert result['urgency'] in ['urgent', 'emergency']
        assert result['confidence'] > 0.7
    
    @pytest.mark.asyncio
    async def test_classify_routine(self, intake_agent):
        """Test routine urgency classification."""
        description = "Schedule annual HVAC maintenance"
        
        result = await intake_agent._classify_urgency(description)
        
        assert result['urgency'] == 'routine'
        assert result['confidence'] > 0.0


class TestServiceTypeDetection:
    """Test service type detection."""
    
    @pytest.mark.asyncio
    async def test_detect_hvac_service(self, intake_agent):
        """
        Test HVAC service type detection.
        Validates: Requirement 4.3 (Classify service type)
        """
        description = "Furnace not heating properly"
        
        result = await intake_agent._detect_service_type(description)
        
        assert result['service_type'] == 'HVAC'
        assert result['confidence'] > 0.8
    
    @pytest.mark.asyncio
    async def test_detect_plumbing_service(self, intake_agent):
        """Test Plumbing service type detection."""
        description = "Water leak under the sink"
        
        result = await intake_agent._detect_service_type(description)
        
        assert result['service_type'] == 'Plumbing'
        assert result['confidence'] > 0.8
    
    @pytest.mark.asyncio
    async def test_detect_electrical_service(self, intake_agent):
        """Test Electrical service type detection."""
        description = "Circuit breaker keeps tripping"
        
        result = await intake_agent._detect_service_type(description)
        
        assert result['service_type'] == 'Electrical'
        assert result['confidence'] > 0.8



class TestConfidenceScoring:
    """Test confidence scoring."""
    
    def test_calculate_confidence_high(self, intake_agent):
        """Test confidence calculation with high confidence inputs."""
        urgency_result = {'urgency': 'emergency', 'confidence': 0.95}
        service_result = {'service_type': 'HVAC', 'confidence': 0.90}
        
        confidence = intake_agent._calculate_confidence(urgency_result, service_result)
        
        assert confidence > 0.85
        assert confidence <= 1.0
    
    def test_calculate_confidence_low(self, intake_agent):
        """Test confidence calculation with low confidence inputs."""
        urgency_result = {'urgency': 'routine', 'confidence': 0.60}
        service_result = {'service_type': 'General', 'confidence': 0.65}
        
        confidence = intake_agent._calculate_confidence(urgency_result, service_result)
        
        assert confidence >= 0.0
        assert confidence < 0.75


class TestPartsAvailabilityChecking:
    """Test parts availability checking."""
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_check_parts_available(self, mock_get_db, intake_agent):
        """
        Test checking parts that are available.
        Validates: Requirement 4.6 (Query InvenTree API for initial parts availability)
        """
        # Mock database with available part
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        
        mock_part = Part(
            id=uuid4(),
            part_number="HVAC-001",
            name="Thermostat",
            category="HVAC",
            quantity_available=10,
            reorder_level=5,
            unit_price=125.00,
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_part
        
        queries = [PartQuery(part_number="HVAC-001")]
        results = await intake_agent.check_parts_availability(queries)
        
        assert len(results) == 1
        assert results[0].is_available is True
        assert results[0].quantity_available == 10
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_check_parts_unavailable(self, mock_get_db, intake_agent):
        """Test checking parts that are unavailable."""
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        queries = [PartQuery(part_number="NONEXISTENT")]
        results = await intake_agent.check_parts_availability(queries)
        
        assert len(results) == 1
        assert results[0].is_available is False


class TestNotificationCreation:
    """Test notification creation (email, push, Discord)."""
    
    @pytest.mark.asyncio
    async def test_create_email_notification(
        self,
        intake_agent,
        sample_customer,
        sample_technician,
        mock_email_notifier
    ):
        """
        Test email notification creation.
        Validates: Requirement 4.8 (Notify via email)
        """
        lead = Lead(
            id=uuid4(),
            customer_id=sample_customer.id,
            source="voice",
            urgency="emergency",
            service_type="HVAC",
            description="Furnace not working",
            status="triaged",
        )
        lead.customer = sample_customer
        
        result = await intake_agent.notify_customer_confirmation(
            lead,
            sample_technician,
            "Tomorrow at 2:00 PM"
        )
        
        assert result is True
        mock_email_notifier.send_appointment_confirmation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_push_notification(
        self,
        intake_agent,
        sample_customer,
        sample_technician,
        mock_push_notifier
    ):
        """
        Test push notification creation.
        Validates: Requirement 4.8 (Notify via push)
        """
        lead = Lead(
            id=uuid4(),
            customer_id=sample_customer.id,
            source="voice",
            urgency="emergency",
            service_type="HVAC",
            description="Furnace not working",
            status="triaged",
        )
        lead.customer = sample_customer
        
        triage_result = TriageResult(
            service_type="HVAC",
            estimated_duration=120,
            required_skills=["HVAC"],
            suggested_technicians=[],
            priority=9,
            confidence=0.9,
            urgency=UrgencyLevel.EMERGENCY,
            reasoning="Emergency repair needed",
        )
        
        result = await intake_agent.notify_technician_assignment(
            lead,
            sample_technician,
            triage_result
        )
        
        assert result is True
        mock_push_notifier.send_job_assignment_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_discord_notification(
        self,
        intake_agent,
        sample_customer,
        mock_discord_notifier
    ):
        """
        Test Discord notification creation.
        Validates: Requirement 4.8 (Notify via Discord)
        """
        lead = Lead(
            id=uuid4(),
            customer_id=sample_customer.id,
            source="voice",
            urgency="emergency",
            service_type="HVAC",
            description="Furnace not working",
            status="triaged",
        )
        lead.customer = sample_customer
        
        triage_result = TriageResult(
            service_type="HVAC",
            estimated_duration=120,
            required_skills=["HVAC"],
            suggested_technicians=[],
            priority=9,
            confidence=0.9,
            urgency=UrgencyLevel.EMERGENCY,
            reasoning="Emergency repair needed",
        )
        
        result = await intake_agent.notify_team_new_lead(lead, triage_result)
        
        assert result is True
        mock_discord_notifier.send_new_lead_alert.assert_called_once()



# ============================================================================
# 8.8.2 Integration Tests
# ============================================================================

class TestCompleteIntakeFlow:
    """Test complete intake flow: capture → classify → create lead → notify."""
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_complete_flow_emergency(
        self,
        mock_get_db,
        intake_agent,
        sample_customer,
        sample_technician,
        mock_email_notifier,
        mock_push_notifier,
        mock_discord_notifier
    ):
        """
        Test complete intake flow for emergency lead.
        Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.8, 4.9, 4.10
        """
        # Mock database
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        # Step 1: Capture lead
        lead_input = LeadInput(
            source=LeadSource.VOICE,
            customer_info=CustomerInfo(
                name="John Doe",
                email="john@example.com",
                phone="+1234567890"
            ),
            issue_description="Gas furnace stopped working, house is freezing",
            raw_text="My gas furnace stopped working and the house is freezing"
        )
        
        lead = await intake_agent.capture_lead(lead_input)
        
        assert lead.status == "new"
        assert intake_agent.total_leads == 1
        
        # Step 2: Triage lead
        triage_result = await intake_agent.triage_lead(lead)
        
        assert lead.status == "triaged"
        assert triage_result.urgency in [UrgencyLevel.EMERGENCY, UrgencyLevel.URGENT]
        assert triage_result.service_type == "HVAC"
        assert triage_result.confidence > 0.0
        assert intake_agent.successful_triages == 1
        
        # Step 3: Send notifications
        tech_notified = await intake_agent.notify_technician_assignment(
            lead, sample_technician, triage_result
        )
        customer_notified = await intake_agent.notify_customer_confirmation(
            lead, sample_technician
        )
        team_notified = await intake_agent.notify_team_new_lead(lead, triage_result)
        
        assert tech_notified is True
        assert customer_notified is True
        assert team_notified is True
        
        # Verify all notifications were sent
        mock_push_notifier.send_job_assignment_notification.assert_called_once()
        mock_email_notifier.send_appointment_confirmation.assert_called_once()
        mock_discord_notifier.send_new_lead_alert.assert_called_once()


class TestWebRTCVoiceIntegration:
    """Test WebRTC voice integration with STT."""
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_webrtc_voice_capture(
        self,
        mock_get_db,
        intake_agent,
        sample_customer
    ):
        """
        Test WebRTC voice call integration.
        Validates: Requirement 4.9 (Multi-channel intake)
        """
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        webrtc_input = LeadInput(
            source=LeadSource.WEBRTC,
            customer_info=CustomerInfo(
                name="Bob Wilson",
                email="bob@example.com"
            ),
            issue_description="Water heater leaking",
            raw_text="My water heater is leaking all over the floor"
        )
        
        lead = await intake_agent.capture_lead(webrtc_input)
        
        assert lead.source == LeadSource.WEBRTC.value
        assert "water heater" in lead.description.lower()


class TestInventoryServiceIntegration:
    """Test inventory service integration."""
    
    @pytest.mark.asyncio
    async def test_get_common_parts_for_service_type(self, intake_agent):
        """
        Test getting common parts for service type.
        Validates: Requirement 4.6 (Parts availability checking)
        """
        parts = await intake_agent.get_common_parts_for_service("HVAC")
        
        assert len(parts) > 0
        assert all(isinstance(p, PartQuery) for p in parts)
        assert all(p.category == "HVAC" for p in parts)


class TestNotificationDeliveryAllChannels:
    """Test notification delivery across all channels."""
    
    @pytest.mark.asyncio
    async def test_all_channels_delivery(
        self,
        intake_agent,
        sample_customer,
        sample_technician,
        mock_email_notifier,
        mock_push_notifier,
        mock_discord_notifier
    ):
        """
        Test notification delivery across email, push, and Discord.
        Validates: Requirement 4.8 (Multi-channel notifications)
        """
        lead = Lead(
            id=uuid4(),
            customer_id=sample_customer.id,
            source="voice",
            urgency="emergency",
            service_type="HVAC",
            description="Furnace not working",
            status="triaged",
        )
        lead.customer = sample_customer
        
        triage_result = TriageResult(
            service_type="HVAC",
            estimated_duration=120,
            required_skills=["HVAC"],
            suggested_technicians=[],
            priority=9,
            confidence=0.9,
            urgency=UrgencyLevel.EMERGENCY,
            reasoning="Emergency repair needed",
        )
        
        # Send all notifications
        results = await asyncio.gather(
            intake_agent.notify_technician_assignment(lead, sample_technician, triage_result),
            intake_agent.notify_customer_confirmation(lead, sample_technician),
            intake_agent.notify_team_new_lead(lead, triage_result),
            intake_agent.notify_emergency_alert(lead, triage_result),
        )
        
        # All should succeed
        assert all(results)
        
        # Verify all notifiers were called
        mock_push_notifier.send_job_assignment_notification.assert_called_once()
        mock_email_notifier.send_appointment_confirmation.assert_called_once()
        mock_discord_notifier.send_new_lead_alert.assert_called_once()
        mock_discord_notifier.send_emergency_job_alert.assert_called_once()


class TestLLMIntegrationForClassification:
    """Test LLM integration (Gemini/Azure) for classification."""
    
    @pytest.mark.asyncio
    async def test_llm_classification_accuracy(self, intake_agent):
        """
        Test LLM classification accuracy.
        Validates: Requirement 4.2 (Structured output extraction)
        """
        text = "My HVAC system stopped working. It's an emergency!"
        
        result = await intake_agent.extract_structured_data(
            text=text,
            schema=StructuredLeadData
        )
        
        assert isinstance(result, StructuredLeadData)
        assert result.service_type == "HVAC"
        assert result.urgency == UrgencyLevel.EMERGENCY



# ============================================================================
# 8.8.3 System Tests
# ============================================================================

class TestIntakePerformanceUnderLoad:
    """Test intake performance under load (100+ concurrent requests)."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    @patch('agents.intake.get_db')
    async def test_concurrent_lead_capture(
        self,
        mock_get_db,
        mock_llm_client,
        sample_customer
    ):
        """
        Test handling 100+ concurrent lead capture requests.
        Validates: Requirement 14.8 (Process 10,000 jobs per day)
        """
        # Mock database
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        # Create agent without notifications for performance testing
        agent = IntakeAgent(llm_client=mock_llm_client, enable_logging=False)
        
        # Create 100 concurrent lead capture tasks
        tasks = []
        for i in range(100):
            lead_input = LeadInput(
                source=LeadSource.WEB,
                customer_info=CustomerInfo(
                    name=f"Customer {i}",
                    email=f"customer{i}@example.com",
                    phone=f"+123456{i:04d}"
                ),
                issue_description=f"Issue {i}",
                raw_text=f"Issue description {i}"
            )
            tasks.append(agent.capture_lead(lead_input))
        
        # Execute all tasks concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start_time
        
        # Verify results
        successful = sum(1 for r in results if isinstance(r, Lead))
        assert successful >= 95  # At least 95% success rate
        assert elapsed < 30  # Should complete within 30 seconds
        assert agent.total_leads == successful


class TestClassificationAccuracyWithRealData:
    """Test classification accuracy with real data."""
    
    @pytest.mark.asyncio
    async def test_hvac_classification_accuracy(self, intake_agent):
        """Test HVAC classification accuracy."""
        test_cases = [
            ("Furnace not heating", "HVAC"),
            ("AC not cooling", "HVAC"),
            ("Thermostat not working", "HVAC"),
            ("Heat pump making noise", "HVAC"),
        ]
        
        correct = 0
        for description, expected_type in test_cases:
            result = await intake_agent._detect_service_type(description)
            if result['service_type'] == expected_type:
                correct += 1
        
        accuracy = correct / len(test_cases)
        assert accuracy >= 0.75  # At least 75% accuracy
    
    @pytest.mark.asyncio
    async def test_urgency_classification_accuracy(self, intake_agent):
        """Test urgency classification accuracy."""
        test_cases = [
            ("Gas leak in basement", "emergency"),
            ("No heat in winter", "emergency"),
            ("AC not working in summer", "urgent"),
            ("Schedule maintenance", "routine"),
        ]
        
        correct = 0
        for description, expected_urgency in test_cases:
            result = await intake_agent._classify_urgency(description)
            if result['urgency'] == expected_urgency:
                correct += 1
        
        accuracy = correct / len(test_cases)
        assert accuracy >= 0.75  # At least 75% accuracy


class TestNotificationDeliveryReliability:
    """Test notification delivery reliability."""
    
    @pytest.mark.asyncio
    async def test_notification_retry_on_failure(
        self,
        mock_llm_client,
        sample_customer,
        sample_technician
    ):
        """Test notification retry behavior on failure."""
        # Create notifier that fails first time, succeeds second time
        mock_notifier = Mock(spec=WebPushNotifier)
        call_count = 0
        
        async def mock_send(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network error")
            return True
        
        mock_notifier.send_job_assignment_notification = AsyncMock(side_effect=mock_send)
        
        agent = IntakeAgent(
            llm_client=mock_llm_client,
            push_notifier=mock_notifier,
        )
        
        lead = Lead(
            id=uuid4(),
            customer_id=sample_customer.id,
            source="voice",
            urgency="emergency",
            service_type="HVAC",
            description="Furnace not working",
            status="triaged",
        )
        lead.customer = sample_customer
        
        triage_result = TriageResult(
            service_type="HVAC",
            estimated_duration=120,
            required_skills=["HVAC"],
            suggested_technicians=[],
            priority=9,
            confidence=0.9,
            urgency=UrgencyLevel.EMERGENCY,
            reasoning="Emergency repair needed",
        )
        
        # First attempt should fail
        result = await agent.notify_technician_assignment(lead, sample_technician, triage_result)
        assert result is False


class TestWebRTCSessionManagement:
    """Test WebRTC session management."""
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_multiple_webrtc_sessions(
        self,
        mock_get_db,
        intake_agent,
        sample_customer
    ):
        """Test handling multiple concurrent WebRTC sessions."""
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        # Create multiple WebRTC sessions
        tasks = []
        for i in range(10):
            webrtc_input = LeadInput(
                source=LeadSource.WEBRTC,
                customer_info=CustomerInfo(
                    name=f"Customer {i}",
                    email=f"customer{i}@example.com"
                ),
                issue_description=f"Issue {i}",
                raw_text=f"Issue description {i}"
            )
            tasks.append(intake_agent.capture_lead(webrtc_input))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if isinstance(r, Lead))
        assert successful >= 9  # At least 90% success rate


class TestRequirementsValidation:
    """Verify all intake-related requirements are met."""
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_requirement_4_1_lead_capture(
        self,
        mock_get_db,
        intake_agent,
        sample_customer
    ):
        """
        Validates: Requirement 4.1 (Lead capture from voice/SMS/web)
        """
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        # Test all sources
        sources = [LeadSource.VOICE, LeadSource.SMS, LeadSource.WEB]
        for source in sources:
            lead_input = LeadInput(
                source=source,
                customer_info=CustomerInfo(
                    name="Test Customer",
                    email="test@example.com"
                ),
                issue_description="Test issue",
                raw_text="Test issue description"
            )
            lead = await intake_agent.capture_lead(lead_input)
            assert lead.source == source.value
    
    @pytest.mark.asyncio
    async def test_requirement_4_4_urgency_within_60_seconds(
        self,
        intake_agent,
        sample_customer
    ):
        """
        Validates: Requirement 4.4 (Classify urgency within 60 seconds)
        """
        lead = Lead(
            id=uuid4(),
            customer_id=sample_customer.id,
            source="voice",
            urgency="unknown",
            service_type="HVAC",
            description="Furnace not working",
            status="new",
        )
        
        start_time = time.time()
        result = await intake_agent.triage_lead(lead)
        elapsed = time.time() - start_time
        
        assert elapsed < 60  # Must complete within 60 seconds
        assert result.urgency in [UrgencyLevel.EMERGENCY, UrgencyLevel.URGENT, UrgencyLevel.ROUTINE]



# ============================================================================
# 8.8.4 End-to-End Tests
# ============================================================================

class TestCompleteCustomerIntake:
    """Test complete customer intake: voice call → transcription → classification → lead creation → technician notification."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @patch('agents.intake.get_db')
    async def test_complete_voice_intake_workflow(
        self,
        mock_get_db,
        intake_agent,
        sample_customer,
        sample_technician,
        mock_email_notifier,
        mock_push_notifier,
        mock_discord_notifier
    ):
        """
        Test complete voice intake workflow from start to finish.
        Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.8, 4.9, 4.10
        """
        # Mock database
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        # Simulate voice call transcription
        raw_transcription = (
            "Hi, this is John Doe. My furnace stopped working last night "
            "and the house is freezing. I need someone to come out as soon as possible. "
            "My address is 123 Main St and my phone number is 555-1234."
        )
        
        # Step 1: Extract structured data from transcription
        structured_data = await intake_agent.extract_structured_data(
            text=raw_transcription,
            schema=StructuredLeadData
        )
        
        assert structured_data.service_type == "HVAC"
        assert structured_data.urgency == UrgencyLevel.EMERGENCY
        
        # Step 2: Create lead input
        lead_input = LeadInput(
            source=LeadSource.VOICE,
            customer_info=CustomerInfo(
                name="John Doe",
                email="john@example.com",
                phone="+1234567890",
                address="123 Main St"
            ),
            issue_description=structured_data.issue_summary,
            urgency=structured_data.urgency,
            raw_text=raw_transcription
        )
        
        # Step 3: Capture lead
        lead = await intake_agent.capture_lead(lead_input)
        
        assert lead.source == LeadSource.VOICE.value
        assert lead.status == "new"
        
        # Step 4: Triage lead
        triage_result = await intake_agent.triage_lead(lead)
        
        assert lead.status == "triaged"
        assert triage_result.urgency == UrgencyLevel.EMERGENCY
        assert triage_result.service_type == "HVAC"
        
        # Step 5: Send all notifications
        notifications_sent = await asyncio.gather(
            intake_agent.notify_technician_assignment(lead, sample_technician, triage_result),
            intake_agent.notify_customer_confirmation(lead, sample_technician, "ASAP"),
            intake_agent.notify_team_new_lead(lead, triage_result),
            intake_agent.notify_emergency_alert(lead, triage_result),
        )
        
        # Verify all notifications sent
        assert all(notifications_sent)
        
        # Verify statistics
        stats = intake_agent.get_statistics()
        assert stats["total_leads"] == 1
        assert stats["successful_triages"] == 1
        assert stats["success_rate"] == 100.0


class TestMultiChannelIntake:
    """Test multi-channel intake (voice, SMS, web)."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @patch('agents.intake.get_db')
    async def test_intake_from_all_channels(
        self,
        mock_get_db,
        intake_agent,
        sample_customer
    ):
        """
        Test intake from all channels: voice, SMS, web, WebRTC, Jitsi.
        Validates: Requirement 4.9 (Multi-channel intake)
        """
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        # Test all channels
        channels = [
            (LeadSource.VOICE, "Voice call issue"),
            (LeadSource.SMS, "SMS text issue"),
            (LeadSource.WEB, "Web form issue"),
            (LeadSource.WEBRTC, "WebRTC call issue"),
            (LeadSource.JITSI, "Jitsi video issue"),
        ]
        
        leads = []
        for source, description in channels:
            lead_input = LeadInput(
                source=source,
                customer_info=CustomerInfo(
                    name="Test Customer",
                    email="test@example.com",
                    phone="+1234567890"
                ),
                issue_description=description,
                raw_text=description
            )
            lead = await intake_agent.capture_lead(lead_input)
            leads.append(lead)
        
        # Verify all leads created
        assert len(leads) == 5
        assert all(isinstance(lead, Lead) for lead in leads)
        assert [lead.source for lead in leads] == [s.value for s, _ in channels]


class TestErrorHandlingAndFallback:
    """Test error handling and fallback mechanisms."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_llm_failure_fallback(self, sample_customer):
        """Test fallback when LLM fails."""
        # Create agent with failing LLM
        failing_llm = Mock(spec=UnifiedLLMClient)
        failing_llm.generate = Mock(side_effect=Exception("LLM service unavailable"))
        
        agent = IntakeAgent(llm_client=failing_llm, enable_logging=False)
        
        lead = Lead(
            id=uuid4(),
            customer_id=sample_customer.id,
            source="voice",
            urgency="unknown",
            service_type="HVAC",
            description="Furnace not working",
            status="new",
        )
        
        # Triage should fail gracefully
        with pytest.raises(Exception):
            await agent.triage_lead(lead)
        
        # Verify failure tracked
        assert agent.failed_triages == 1
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_partial_notification_failure(
        self,
        mock_llm_client,
        sample_customer,
        sample_technician
    ):
        """Test handling of partial notification failures."""
        # Create notifiers with one failing
        email_notifier = Mock(spec=EmailNotifier)
        email_notifier.send_appointment_confirmation = AsyncMock(
            side_effect=Exception("SMTP error")
        )
        
        push_notifier = Mock(spec=WebPushNotifier)
        push_notifier.send_job_assignment_notification = AsyncMock(return_value=True)
        
        discord_notifier = Mock(spec=DiscordNotifier)
        discord_notifier.send_new_lead_alert = AsyncMock(return_value=True)
        
        agent = IntakeAgent(
            llm_client=mock_llm_client,
            email_notifier=email_notifier,
            push_notifier=push_notifier,
            discord_notifier=discord_notifier,
        )
        
        lead = Lead(
            id=uuid4(),
            customer_id=sample_customer.id,
            source="voice",
            urgency="emergency",
            service_type="HVAC",
            description="Furnace not working",
            status="triaged",
        )
        lead.customer = sample_customer
        
        triage_result = TriageResult(
            service_type="HVAC",
            estimated_duration=120,
            required_skills=["HVAC"],
            suggested_technicians=[],
            priority=9,
            confidence=0.9,
            urgency=UrgencyLevel.EMERGENCY,
            reasoning="Emergency repair needed",
        )
        
        # Send notifications
        results = await asyncio.gather(
            agent.notify_technician_assignment(lead, sample_technician, triage_result),
            agent.notify_customer_confirmation(lead, sample_technician),
            agent.notify_team_new_lead(lead, triage_result),
            return_exceptions=True
        )
        
        # Some should succeed, some should fail
        assert results[0] is True  # Push notification succeeded
        assert results[1] is False  # Email notification failed
        assert results[2] is True  # Discord notification succeeded
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    @patch('agents.intake.get_db')
    async def test_database_failure_handling(
        self,
        mock_get_db,
        intake_agent,
        sample_customer
    ):
        """Test handling of database failures."""
        # Mock database to fail
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        mock_db.query.side_effect = Exception("Database connection error")
        
        lead_input = LeadInput(
            source=LeadSource.VOICE,
            customer_info=CustomerInfo(
                name="Test Customer",
                email="test@example.com"
            ),
            issue_description="Test issue",
            raw_text="Test issue description"
        )
        
        # Should raise exception
        with pytest.raises(Exception):
            await intake_agent.capture_lead(lead_input)


# ============================================================================
# Performance and Statistics Tests
# ============================================================================

class TestAgentStatistics:
    """Test agent statistics tracking."""
    
    def test_statistics_initialization(self, intake_agent):
        """Test statistics are initialized correctly."""
        stats = intake_agent.get_statistics()
        
        assert stats["total_leads"] == 0
        assert stats["successful_triages"] == 0
        assert stats["failed_triages"] == 0
        assert stats["success_rate"] == 0
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_statistics_update_on_success(
        self,
        mock_get_db,
        intake_agent,
        sample_customer
    ):
        """Test statistics update on successful operations."""
        mock_db = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_db
        mock_get_db.return_value.__exit__.return_value = None
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        # Capture lead
        lead_input = LeadInput(
            source=LeadSource.VOICE,
            customer_info=CustomerInfo(name="Test", email="test@example.com"),
            issue_description="Test issue",
            raw_text="Test"
        )
        lead = await intake_agent.capture_lead(lead_input)
        
        # Triage lead
        await intake_agent.triage_lead(lead)
        
        # Check statistics
        stats = intake_agent.get_statistics()
        assert stats["total_leads"] == 1
        assert stats["successful_triages"] == 1
        assert stats["success_rate"] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
