"""
Tests for Intake Agent
Validates Requirements 4.1, 4.2, 4.9
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from uuid import uuid4

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio

from agents.intake import (
    IntakeAgent,
    LeadInput,
    LeadSource,
    UrgencyLevel,
    CustomerInfo,
    TriageResult,
    StructuredLeadData,
    create_intake_agent,
)
from llm.unified_client import UnifiedLLMClient, LLMResponse
from db.models import Lead, Customer


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = Mock(spec=UnifiedLLMClient)
    
    # Mock generate method
    def mock_generate(prompt, **kwargs):
        # Return different responses based on prompt content
        if "triage" in prompt.lower() or "classify" in prompt.lower():
            return LLMResponse(
                text=(
                    "Service Type: HVAC\n"
                    "Urgency: emergency\n"
                    "Estimated Duration: 120 minutes\n"
                    "Required Skills: HVAC, electrical\n"
                    "Priority: 9\n"
                    "Reasoning: Furnace failure in winter is an emergency requiring immediate attention."
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
def intake_agent(mock_llm_client):
    """Create Intake Agent instance."""
    return IntakeAgent(llm_client=mock_llm_client, enable_logging=False)


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


@pytest.fixture
def sample_customer():
    """Create sample customer."""
    return Customer(
        id=uuid4(),
        name="John Doe",
        email="john@example.com",
        phone="+1234567890",
        address="123 Main St",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def sample_lead(sample_customer):
    """Create sample lead."""
    return Lead(
        id=uuid4(),
        customer_id=sample_customer.id,
        source="voice",
        urgency="emergency",
        service_type="HVAC",
        description="Furnace stopped working",
        confidence_score=0.0,
        status="new",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


# ============================================================================
# Unit Tests
# ============================================================================

class TestIntakeAgentInitialization:
    """Test Intake Agent initialization."""
    
    def test_init_success(self, mock_llm_client):
        """Test successful initialization."""
        agent = IntakeAgent(llm_client=mock_llm_client)
        
        assert agent.llm_client == mock_llm_client
        assert agent.total_leads == 0
        assert agent.successful_triages == 0
        assert agent.failed_triages == 0
        # Simplified implementation uses role strings instead of CrewAI agents
        assert agent.capture_role is not None
        assert agent.triage_role is not None
        assert agent.scheduling_role is not None
    
    def test_factory_function(self, mock_llm_client):
        """Test factory function."""
        agent = create_intake_agent(llm_client=mock_llm_client)
        
        assert isinstance(agent, IntakeAgent)
        assert agent.llm_client == mock_llm_client


class TestStructuredDataExtraction:
    """Test structured data extraction with PydanticAI."""
    
    @pytest.mark.asyncio
    async def test_extract_structured_data(self, intake_agent):
        """
        Test structured output extraction.
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
        assert "stopped working" in result.issue_summary.lower()
    
    @pytest.mark.asyncio
    async def test_extract_with_missing_fields(self, intake_agent):
        """Test extraction with incomplete information."""
        text = "Something is broken"
        
        result = await intake_agent.extract_structured_data(
            text=text,
            schema=StructuredLeadData
        )
        
        assert isinstance(result, StructuredLeadData)
        # Should have defaults for missing fields
        assert result.service_type is not None
        assert result.urgency is not None


class TestLeadCapture:
    """Test lead capture from multiple sources."""
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_capture_lead_from_voice(
        self,
        mock_get_db,
        intake_agent,
        sample_lead_input,
        sample_customer
    ):
        """
        Test lead capture from voice source.
        Validates: Requirement 4.1 (Lead capture from voice)
        """
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        lead = await intake_agent.capture_lead(sample_lead_input)
        
        assert isinstance(lead, Lead)
        assert lead.source == LeadSource.VOICE.value
        assert lead.customer_id == sample_customer.id
        assert lead.status == "new"
        assert intake_agent.total_leads == 1
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_capture_lead_from_web(
        self,
        mock_get_db,
        intake_agent,
        sample_customer
    ):
        """
        Test lead capture from web source.
        Validates: Requirement 4.1 (Lead capture from web)
        """
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        web_input = LeadInput(
            source=LeadSource.WEB,
            customer_info=CustomerInfo(
                name="Jane Smith",
                email="jane@example.com",
                phone="+1987654321"
            ),
            issue_description="Need plumbing repair",
            raw_text="Need plumbing repair for leaking faucet"
        )
        
        lead = await intake_agent.capture_lead(web_input)
        
        assert lead.source == LeadSource.WEB.value
        assert intake_agent.total_leads == 1
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_capture_lead_from_sms(
        self,
        mock_get_db,
        intake_agent,
        sample_customer
    ):
        """
        Test lead capture from SMS source.
        Validates: Requirement 4.1 (Lead capture from SMS)
        """
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        sms_input = LeadInput(
            source=LeadSource.SMS,
            customer_info=CustomerInfo(
                phone="+1234567890"
            ),
            issue_description="AC not cooling",
            raw_text="AC not cooling need help"
        )
        
        lead = await intake_agent.capture_lead(sms_input)
        
        assert lead.source == LeadSource.SMS.value
        assert intake_agent.total_leads == 1


class TestLeadTriage:
    """Test lead triage and classification."""
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_triage_emergency(
        self,
        mock_get_db,
        intake_agent,
        sample_lead
    ):
        """
        Test emergency classification.
        Validates: Requirement 4.4 (Classify urgency within 60 seconds)
        """
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        import time
        start_time = time.time()
        
        result = await intake_agent.triage_lead(sample_lead)
        
        elapsed = time.time() - start_time
        
        assert isinstance(result, TriageResult)
        assert result.urgency == UrgencyLevel.EMERGENCY
        assert result.service_type == "HVAC"
        assert result.priority >= 8  # High priority for emergency
        assert elapsed < 60  # Must complete within 60 seconds
        assert intake_agent.successful_triages == 1
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_triage_routine(
        self,
        mock_get_db,
        intake_agent
    ):
        """Test routine service classification."""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        # Create routine lead
        routine_lead = Lead(
            id=uuid4(),
            customer_id=uuid4(),
            source="web",
            urgency="routine",
            service_type="General",
            description="Schedule annual maintenance",
            confidence_score=0.0,
            status="new",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        result = await intake_agent.triage_lead(routine_lead)
        
        assert isinstance(result, TriageResult)
        assert result.priority <= 5  # Lower priority for routine
        assert result.confidence > 0.0
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_triage_updates_lead(
        self,
        mock_get_db,
        intake_agent,
        sample_lead
    ):
        """Test that triage updates lead record."""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        original_status = sample_lead.status
        
        result = await intake_agent.triage_lead(sample_lead)
        
        assert sample_lead.status == "triaged"
        assert sample_lead.status != original_status
        assert sample_lead.confidence_score > 0.0


class TestMultiSourceIntegration:
    """Test multi-source integration."""
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_webrtc_integration(
        self,
        mock_get_db,
        intake_agent,
        sample_customer
    ):
        """
        Test WebRTC voice call integration.
        Validates: Requirement 4.9 (Multi-source integration)
        """
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
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
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_jitsi_video_integration(
        self,
        mock_get_db,
        intake_agent,
        sample_customer
    ):
        """
        Test Jitsi video consultation integration.
        Validates: Requirement 4.9 (Multi-source integration)
        """
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        jitsi_input = LeadInput(
            source=LeadSource.JITSI,
            customer_info=CustomerInfo(
                name="Alice Brown",
                email="alice@example.com"
            ),
            issue_description="Complex electrical issue needs video consultation",
            raw_text="I have a complex electrical issue that needs video consultation"
        )
        
        lead = await intake_agent.capture_lead(jitsi_input)
        
        assert lead.source == LeadSource.JITSI.value


class TestAgentStatistics:
    """Test agent statistics tracking."""
    
    def test_get_statistics(self, intake_agent):
        """Test statistics retrieval."""
        stats = intake_agent.get_statistics()
        
        assert "total_leads" in stats
        assert "successful_triages" in stats
        assert "failed_triages" in stats
        assert "success_rate" in stats
        assert stats["total_leads"] == 0
        assert stats["success_rate"] == 0
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_statistics_update(
        self,
        mock_get_db,
        intake_agent,
        sample_lead
    ):
        """Test that statistics update correctly."""
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        
        initial_stats = intake_agent.get_statistics()
        
        await intake_agent.triage_lead(sample_lead)
        
        updated_stats = intake_agent.get_statistics()
        
        assert updated_stats["successful_triages"] > initial_stats["successful_triages"]
        assert updated_stats["success_rate"] > 0


class TestErrorHandling:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_triage_with_llm_failure(self, sample_lead):
        """Test triage handling when LLM fails."""
        # Create agent with failing LLM client
        failing_client = Mock(spec=UnifiedLLMClient)
        failing_client.generate = Mock(side_effect=Exception("LLM error"))
        
        agent = IntakeAgent(llm_client=failing_client, enable_logging=False)
        
        with pytest.raises(Exception):
            await agent.triage_lead(sample_lead)
        
        assert agent.failed_triages == 1
    
    @pytest.mark.asyncio
    async def test_extraction_with_invalid_response(self, intake_agent):
        """Test extraction with invalid LLM response."""
        # Override mock to return invalid JSON
        intake_agent.llm_client.generate = Mock(
            return_value=LLMResponse(
                text="This is not valid JSON",
                model="gemini-2.5-flash",
                usage={},
                metadata={}
            )
        )
        
        result = await intake_agent.extract_structured_data(
            text="Some text",
            schema=StructuredLeadData
        )
        
        # Should return default values instead of crashing
        assert isinstance(result, StructuredLeadData)


# ============================================================================
# Integration Tests
# ============================================================================

class TestEndToEndWorkflow:
    """Test end-to-end intake workflow."""
    
    @pytest.mark.asyncio
    @patch('agents.intake.get_db')
    async def test_complete_intake_workflow(
        self,
        mock_get_db,
        intake_agent,
        sample_lead_input,
        sample_customer
    ):
        """
        Test complete intake workflow from capture to triage.
        Validates: Requirements 4.1, 4.2, 4.4, 4.9
        """
        # Mock database session
        mock_db = AsyncMock()
        mock_get_db.return_value.__aenter__.return_value = mock_db
        mock_db.query.return_value.filter.return_value.first.return_value = sample_customer
        
        # Step 1: Capture lead
        lead = await intake_agent.capture_lead(sample_lead_input)
        
        assert lead.status == "new"
        assert intake_agent.total_leads == 1
        
        # Step 2: Triage lead
        triage_result = await intake_agent.triage_lead(lead)
        
        assert lead.status == "triaged"
        assert triage_result.urgency in [
            UrgencyLevel.EMERGENCY,
            UrgencyLevel.URGENT,
            UrgencyLevel.ROUTINE
        ]
        assert triage_result.confidence > 0.0
        assert intake_agent.successful_triages == 1
        
        # Step 3: Verify statistics
        stats = intake_agent.get_statistics()
        assert stats["total_leads"] == 1
        assert stats["successful_triages"] == 1
        assert stats["success_rate"] == 100.0
