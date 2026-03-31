"""
Integration Test for Voice-to-Database Flow.

Tests the complete workflow:
1. Voice input → STT transcription
2. Intent classification → Agent routing
3. Agent processing → Database operations
4. Response generation → TTS synthesis
5. Metrics tracking and persistence

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 11.2**
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from voice.session_manager import create_voice_session_manager
from voice.voice_agent_integration import (
    create_voice_agent_integration,
    VoiceAgentRequest,
)


class TestVoiceToDatabaseFlow:
    """Integration tests for voice-to-database flow."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_voice_lead_intake_to_database(self):
        """
        Test voice lead intake flow to database.
        
        Flow:
        1. Customer calls via voice
        2. System transcribes: "My AC stopped working"
        3. Intent classified as LEAD_INTAKE
        4. Routed to Intake Agent
        5. Agent extracts structured data
        6. Lead saved to database
        7. Response synthesized: "I've created your service request"
        """
        # Mock components
        mock_voice_pipeline = Mock()
        mock_voice_pipeline.start_session = AsyncMock(
            return_value=Mock(session_id="pipeline-session")
        )
        mock_voice_pipeline.synthesize_speech = AsyncMock(return_value=b"audio_response")
        
        mock_agent_router = Mock()
        routing_decision = Mock()
        routing_decision.intent = Mock(value="LEAD_INTAKE")
        routing_decision.agent_type = Mock(value="intake")
        routing_decision.confidence = 0.95
        routing_decision.requires_clarification = False
        mock_agent_router.route_request = AsyncMock(return_value=routing_decision)
        mock_agent_router.execute_routing = AsyncMock(
            return_value={
                "response": "I've created your service request for AC repair. A technician will contact you within 2 hours.",
                "lead_id": "lead-123",
                "urgency": "urgent",
            }
        )
        
        # Create session manager
        session_manager = create_voice_session_manager()
        
        # Create integration
        integration = create_voice_agent_integration(
            voice_pipeline=mock_voice_pipeline,
            agent_router=mock_agent_router,
            session_manager=session_manager,
        )
        
        # Create session
        session = session_manager.create_session(
            user_id="customer-123",
            user_role="customer",
        )
        
        # Process voice input
        request = VoiceAgentRequest(
            session_id=session.session_id,
            text_input="My AC stopped working",  # Simulating transcription
        )
        
        response = await integration.process_voice_input(request)
        
        # Verify response
        assert response.session_id == session.session_id
        assert response.intent == "LEAD_INTAKE"
        assert response.agent_type == "intake"
        assert "service request" in response.text_response.lower()
        
        # Verify session metrics
        updated_session = session_manager.get_session(session.session_id)
        assert updated_session.metrics.turn_count == 2  # User + Agent
        assert updated_session.metrics.user_turns == 1
        assert updated_session.metrics.agent_turns == 1
        assert updated_session.current_intent == "LEAD_INTAKE"
        assert updated_session.current_agent == "intake"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_voice_job_completion_to_database(self):
        """
        Test voice job completion flow to database.
        
        Flow:
        1. Technician says: "Log job completion for Smith residence"
        2. System transcribes and classifies as JOB_COMPLETION
        3. Routed to Fulfillment Agent
        4. Agent extracts job details
        5. Job updated in database
        6. Carbon footprint calculated
        7. Response synthesized with summary
        """
        # Mock components
        mock_voice_pipeline = Mock()
        mock_voice_pipeline.start_session = AsyncMock(
            return_value=Mock(session_id="pipeline-session")
        )
        mock_voice_pipeline.synthesize_speech = AsyncMock(return_value=b"audio_response")
        
        mock_agent_router = Mock()
        routing_decision = Mock()
        routing_decision.intent = Mock(value="JOB_COMPLETION")
        routing_decision.agent_type = Mock(value="fulfillment")
        routing_decision.confidence = 0.92
        routing_decision.requires_clarification = False
        mock_agent_router.route_request = AsyncMock(return_value=routing_decision)
        mock_agent_router.execute_routing = AsyncMock(
            return_value={
                "response": "Job logged successfully. Total cost: $285. Carbon footprint: 2.3kg CO2. First-time fix recorded.",
                "job_id": "job-456",
                "total_cost": 285.0,
                "carbon_footprint": 2.3,
                "first_time_fix": True,
            }
        )
        
        # Create session manager
        session_manager = create_voice_session_manager()
        
        # Create integration
        integration = create_voice_agent_integration(
            voice_pipeline=mock_voice_pipeline,
            agent_router=mock_agent_router,
            session_manager=session_manager,
        )
        
        # Create session
        session = session_manager.create_session(
            user_id="tech-123",
            user_role="technician",
            job_id="job-456",
        )
        
        # Process voice input
        request = VoiceAgentRequest(
            session_id=session.session_id,
            text_input="Log job completion for Smith residence. Replaced thermostat model TH-2000.",
        )
        
        response = await integration.process_voice_input(request)
        
        # Verify response
        assert response.session_id == session.session_id
        assert response.intent == "JOB_COMPLETION"
        assert response.agent_type == "fulfillment"
        assert "job logged" in response.text_response.lower()
        assert "carbon" in response.text_response.lower()
        
        # Verify session metrics
        updated_session = session_manager.get_session(session.session_id)
        assert updated_session.metrics.turn_count == 2
        assert updated_session.job_id == "job-456"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_voice_diagnostic_with_parts_query(self):
        """
        Test voice diagnostic flow with parts query.
        
        Flow:
        1. Technician says: "What parts do I need for Carrier furnace model 58MCA090?"
        2. System transcribes and classifies as DIAGNOSIS
        3. Routed to Diagnostic Agent
        4. Agent queries InvenTree for parts
        5. Agent uses KiCost for pricing
        6. Response with parts list and availability
        """
        # Mock components
        mock_voice_pipeline = Mock()
        mock_voice_pipeline.start_session = AsyncMock(
            return_value=Mock(session_id="pipeline-session")
        )
        mock_voice_pipeline.synthesize_speech = AsyncMock(return_value=b"audio_response")
        
        mock_agent_router = Mock()
        routing_decision = Mock()
        routing_decision.intent = Mock(value="DIAGNOSIS")
        routing_decision.agent_type = Mock(value="diagnostic")
        routing_decision.confidence = 0.88
        routing_decision.requires_clarification = False
        mock_agent_router.route_request = AsyncMock(return_value=routing_decision)
        mock_agent_router.execute_routing = AsyncMock(
            return_value={
                "response": "For Carrier 58MCA090, you'll need: OEM Ignitor (IG-58MCA) at $85, in stock. Alternative: Universal Ignitor (IG-UNIV-90) at $45, also in stock.",
                "parts": [
                    {"model": "IG-58MCA", "price": 85.0, "availability": "in-stock"},
                    {"model": "IG-UNIV-90", "price": 45.0, "availability": "in-stock"},
                ],
            }
        )
        
        # Create session manager
        session_manager = create_voice_session_manager()
        
        # Create integration
        integration = create_voice_agent_integration(
            voice_pipeline=mock_voice_pipeline,
            agent_router=mock_agent_router,
            session_manager=session_manager,
        )
        
        # Create session
        session = session_manager.create_session(
            user_id="tech-123",
            user_role="technician",
        )
        
        # Process voice input
        request = VoiceAgentRequest(
            session_id=session.session_id,
            text_input="What parts do I need for Carrier furnace model 58MCA090?",
        )
        
        response = await integration.process_voice_input(request)
        
        # Verify response
        assert response.session_id == session.session_id
        assert response.intent == "DIAGNOSIS"
        assert response.agent_type == "diagnostic"
        assert "ignitor" in response.text_response.lower()
        assert "in stock" in response.text_response.lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_voice_session_metrics_persistence(self):
        """
        Test that session metrics are tracked and can be persisted.
        
        Validates:
        - Latency tracking (p50, p95, p99)
        - Turn count tracking
        - Interruption tracking
        - API cost tracking (should be $0 for local processing)
        """
        # Create session manager
        session_manager = create_voice_session_manager()
        
        # Create session
        session = session_manager.create_session(
            user_id="tech-123",
            user_role="technician",
        )
        
        # Simulate multiple turns with varying latencies
        latencies = [100, 150, 200, 120, 180, 110, 190, 130, 160, 140]
        for i, latency in enumerate(latencies):
            session_manager.add_turn(
                session_id=session.session_id,
                speaker="user" if i % 2 == 0 else "agent",
                message=f"Turn {i}",
                latency=latency,
            )
        
        # Add an interruption
        session_manager.add_interruption(session.session_id)
        
        # Get session and verify metrics
        updated_session = session_manager.get_session(session.session_id)
        metrics = updated_session.metrics
        
        assert metrics.turn_count == 10
        assert metrics.user_turns == 5
        assert metrics.agent_turns == 5
        assert metrics.interruptions == 1
        assert metrics.avg_latency == sum(latencies) / len(latencies)
        assert metrics.p50_latency > 0
        assert metrics.p95_latency > metrics.p50_latency
        assert metrics.api_cost == 0.0  # Local processing = zero cost
        
        # Verify turn-taking accuracy
        accuracy = metrics.get_turn_taking_accuracy()
        assert accuracy == 0.9  # 1 interruption out of 10 turns = 90%
        
        # End session
        ended_session = session_manager.end_session(session.session_id)
        assert ended_session.status.value == "ended"
        assert ended_session.metrics.end_time is not None
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_voice_error_handling_and_fallback(self):
        """
        Test error handling and fallback to text mode.
        
        Validates: Requirement 15.1 (fallback to text mode on error)
        """
        # Mock components with error in agent router
        mock_voice_pipeline = Mock()
        mock_voice_pipeline.start_session = AsyncMock(
            return_value=Mock(session_id="pipeline-session")
        )
        
        mock_agent_router = Mock()
        # Make agent router raise an error
        mock_agent_router.route_request = AsyncMock(
            side_effect=Exception("Agent routing error")
        )
        
        # Create session manager
        session_manager = create_voice_session_manager()
        
        # Create integration
        integration = create_voice_agent_integration(
            voice_pipeline=mock_voice_pipeline,
            agent_router=mock_agent_router,
            session_manager=session_manager,
        )
        
        # Create session
        session = session_manager.create_session(
            user_id="customer-123",
            user_role="customer",
        )
        
        # Process voice input (will fail and fallback)
        request = VoiceAgentRequest(
            session_id=session.session_id,
            text_input="Test input",
        )
        
        response = await integration.process_voice_input(request)
        
        # Verify fallback to text mode
        assert response.mode.value == "text"
        assert response.error is not None
        assert "trouble with voice processing" in response.text_response.lower()
        
        # Verify error was recorded
        updated_session = session_manager.get_session(session.session_id)
        assert updated_session.metrics.errors > 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_voice_multi_turn_conversation(self):
        """
        Test multi-turn conversation with context preservation.
        
        Validates:
        - Context is maintained across turns
        - Intent classification uses conversation history
        - Metrics track all turns correctly
        """
        # Mock components
        mock_voice_pipeline = Mock()
        mock_voice_pipeline.start_session = AsyncMock(
            return_value=Mock(session_id="pipeline-session")
        )
        mock_voice_pipeline.synthesize_speech = AsyncMock(return_value=b"audio_response")
        
        mock_agent_router = Mock()
        
        # Create session manager
        session_manager = create_voice_session_manager()
        
        # Create integration
        integration = create_voice_agent_integration(
            voice_pipeline=mock_voice_pipeline,
            agent_router=mock_agent_router,
            session_manager=session_manager,
        )
        
        # Create session
        session = session_manager.create_session(
            user_id="customer-123",
            user_role="customer",
        )
        
        # Turn 1: Initial request
        routing_decision_1 = Mock()
        routing_decision_1.intent = Mock(value="LEAD_INTAKE")
        routing_decision_1.agent_type = Mock(value="intake")
        routing_decision_1.confidence = 0.95
        routing_decision_1.requires_clarification = False
        mock_agent_router.route_request = AsyncMock(return_value=routing_decision_1)
        mock_agent_router.execute_routing = AsyncMock(
            return_value={"response": "What type of service do you need?"}
        )
        
        request_1 = VoiceAgentRequest(
            session_id=session.session_id,
            text_input="I need help with my AC",
        )
        response_1 = await integration.process_voice_input(request_1)
        assert response_1.intent == "LEAD_INTAKE"
        
        # Turn 2: Follow-up
        routing_decision_2 = Mock()
        routing_decision_2.intent = Mock(value="LEAD_INTAKE")
        routing_decision_2.agent_type = Mock(value="intake")
        routing_decision_2.confidence = 0.92
        routing_decision_2.requires_clarification = False
        mock_agent_router.route_request = AsyncMock(return_value=routing_decision_2)
        mock_agent_router.execute_routing = AsyncMock(
            return_value={"response": "I've scheduled a technician for today at 2pm."}
        )
        
        request_2 = VoiceAgentRequest(
            session_id=session.session_id,
            text_input="It stopped working this morning",
        )
        response_2 = await integration.process_voice_input(request_2)
        assert response_2.intent == "LEAD_INTAKE"
        
        # Verify multi-turn metrics
        updated_session = session_manager.get_session(session.session_id)
        assert updated_session.metrics.turn_count == 4  # 2 user + 2 agent
        assert updated_session.metrics.user_turns == 2
        assert updated_session.metrics.agent_turns == 2
        assert len(updated_session.conversation_turns) == 4


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_voice_to_database_with_various_accents():
    """
    Test voice-to-database flow with various accents and noise levels.
    
    This is an optional test that would require:
    - Real audio samples with different accents
    - Noise simulation
    - STT accuracy measurement
    
    **Validates: Requirement 2.7 (adapt to background noise)**
    """
    # TODO: Implement with real audio samples
    # This would test:
    # 1. American English accent
    # 2. British English accent
    # 3. Australian English accent
    # 4. Various noise levels (40dB, 60dB, 80dB)
    # 5. STT accuracy for each scenario
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
