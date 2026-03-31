"""
Unit Tests for Voice-to-Agent Integration.

Tests:
- Voice session manager
- Voice-agent integration flow
- Streaming response handling
- Turn-taking detection
- Error handling and fallback

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9, 2.10, 3.1, 3.2, 15.1**
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from voice.session_manager import (
    VoiceSessionManager,
    VoiceSessionModel,
    VoiceSessionMetrics,
    SessionStatus,
    create_voice_session_manager,
)
from voice.voice_agent_integration import (
    VoiceAgentIntegration,
    VoiceAgentRequest,
    VoiceAgentResponse,
    InteractionMode,
    create_voice_agent_integration,
)
from voice.streaming_handler import (
    StreamingResponseHandler,
    TurnTakingDetector,
    StreamEventType,
    create_streaming_handler,
)


# ============================================================================
# Voice Session Manager Tests
# ============================================================================


class TestVoiceSessionMetrics:
    """Test voice session metrics."""
    
    def test_metrics_initialization(self):
        """Test metrics are initialized correctly."""
        metrics = VoiceSessionMetrics(
            session_id="test-session",
            start_time=time.time()
        )
        
        assert metrics.session_id == "test-session"
        assert metrics.turn_count == 0
        assert metrics.user_turns == 0
        assert metrics.agent_turns == 0
        assert metrics.interruptions == 0
        assert metrics.avg_latency == 0.0
        assert metrics.api_cost == 0.0  # Should be zero for local processing
    
    def test_add_latency(self):
        """Test adding latency measurements."""
        metrics = VoiceSessionMetrics(
            session_id="test-session",
            start_time=time.time()
        )
        
        # Add latencies
        metrics.add_latency(100.0)
        metrics.add_latency(200.0)
        metrics.add_latency(150.0)
        
        assert len(metrics.latencies) == 3
        assert metrics.avg_latency == 150.0
        assert metrics.p50_latency == 150.0
    
    def test_turn_taking_accuracy(self):
        """Test turn-taking accuracy calculation."""
        metrics = VoiceSessionMetrics(
            session_id="test-session",
            start_time=time.time()
        )
        
        # Simulate conversation with 1 interruption out of 10 turns
        metrics.user_turns = 5
        metrics.agent_turns = 5
        metrics.interruptions = 1
        
        accuracy = metrics.get_turn_taking_accuracy()
        assert accuracy == 0.9  # 90% accuracy
        
        # Test target: 95%+ accuracy
        metrics.interruptions = 0
        accuracy = metrics.get_turn_taking_accuracy()
        assert accuracy == 1.0  # 100% accuracy
    
    def test_session_duration(self):
        """Test session duration calculation."""
        start_time = time.time()
        metrics = VoiceSessionMetrics(
            session_id="test-session",
            start_time=start_time
        )
        
        time.sleep(0.1)  # Wait 100ms
        
        duration = metrics.get_session_duration()
        assert duration >= 0.1
        
        # End session
        metrics.end_time = time.time()
        duration = metrics.get_session_duration()
        assert duration >= 0.1


class TestVoiceSessionModel:
    """Test voice session model."""
    
    def test_session_creation(self):
        """Test session is created correctly."""
        session = VoiceSessionModel(
            session_id="test-session",
            status=SessionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            user_id="user-123",
            user_role="technician",
        )
        
        assert session.session_id == "test-session"
        assert session.status == SessionStatus.ACTIVE
        assert session.user_id == "user-123"
        assert session.user_role == "technician"
        assert session.metrics is not None
    
    def test_add_turn(self):
        """Test adding conversation turns."""
        session = VoiceSessionModel(
            session_id="test-session",
            status=SessionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        # Add user turn
        session.add_turn(
            speaker="user",
            message="Hello",
            intent="greeting",
            latency=100.0,
        )
        
        assert session.metrics.turn_count == 1
        assert session.metrics.user_turns == 1
        assert session.current_intent == "greeting"
        assert len(session.conversation_turns) == 1
        
        # Add agent turn
        session.add_turn(
            speaker="agent",
            message="Hi there!",
            agent="intake",
        )
        
        assert session.metrics.turn_count == 2
        assert session.metrics.agent_turns == 1
        assert session.current_agent == "intake"
    
    def test_add_interruption(self):
        """Test recording interruptions."""
        session = VoiceSessionModel(
            session_id="test-session",
            status=SessionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        session.add_interruption()
        assert session.metrics.interruptions == 1
    
    def test_end_session(self):
        """Test ending a session."""
        session = VoiceSessionModel(
            session_id="test-session",
            status=SessionStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        session.end_session()
        assert session.status == SessionStatus.ENDED
        assert session.metrics.end_time is not None


class TestVoiceSessionManager:
    """Test voice session manager."""
    
    def test_create_session(self):
        """Test creating a session."""
        manager = create_voice_session_manager()
        
        session = manager.create_session(
            user_id="user-123",
            user_role="technician",
        )
        
        assert session.session_id is not None
        assert session.status == SessionStatus.ACTIVE
        assert session.user_id == "user-123"
        assert manager.total_sessions == 1
        assert manager.active_sessions == 1
    
    def test_get_session(self):
        """Test getting a session."""
        manager = create_voice_session_manager()
        
        session = manager.create_session(user_id="user-123")
        retrieved = manager.get_session(session.session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
    
    def test_end_session(self):
        """Test ending a session."""
        manager = create_voice_session_manager()
        
        session = manager.create_session(user_id="user-123")
        ended = manager.end_session(session.session_id)
        
        assert ended is not None
        assert ended.status == SessionStatus.ENDED
        assert manager.active_sessions == 0
    
    def test_add_turn(self):
        """Test adding a turn to a session."""
        manager = create_voice_session_manager()
        
        session = manager.create_session(user_id="user-123")
        success = manager.add_turn(
            session_id=session.session_id,
            speaker="user",
            message="Hello",
            intent="greeting",
            latency=100.0,
        )
        
        assert success is True
        
        retrieved = manager.get_session(session.session_id)
        assert retrieved.metrics.turn_count == 1
    
    def test_get_active_sessions(self):
        """Test getting active sessions."""
        manager = create_voice_session_manager()
        
        # Create multiple sessions
        session1 = manager.create_session(user_id="user-1")
        session2 = manager.create_session(user_id="user-2")
        
        active = manager.get_active_sessions()
        assert len(active) == 2
        
        # End one session
        manager.end_session(session1.session_id)
        active = manager.get_active_sessions()
        assert len(active) == 1
    
    def test_get_statistics(self):
        """Test getting statistics."""
        manager = create_voice_session_manager()
        
        # Create sessions
        session1 = manager.create_session(user_id="user-1")
        session2 = manager.create_session(user_id="user-2")
        
        # Add turns
        manager.add_turn(session1.session_id, "user", "Hello")
        manager.add_turn(session2.session_id, "user", "Hi")
        
        stats = manager.get_statistics()
        assert stats["total_sessions"] == 2
        assert stats["active_sessions"] == 2
        assert stats["total_turns"] == 2


# ============================================================================
# Voice-Agent Integration Tests
# ============================================================================


class TestVoiceAgentIntegration:
    """Test voice-agent integration."""
    
    @pytest.fixture
    def mock_voice_pipeline(self):
        """Create mock voice pipeline."""
        pipeline = Mock()
        pipeline.start_session = AsyncMock(return_value=Mock(session_id="pipeline-session"))
        pipeline.synthesize_speech = AsyncMock(return_value=b"audio_data")
        pipeline.handle_interruption = Mock(return_value=True)
        return pipeline
    
    @pytest.fixture
    def mock_agent_router(self):
        """Create mock agent router."""
        router = Mock()
        
        # Mock routing decision
        routing_decision = Mock()
        routing_decision.intent = Mock(value="greeting")
        routing_decision.agent_type = Mock(value="intake")
        routing_decision.confidence = 0.95
        routing_decision.requires_clarification = False
        
        router.route_request = AsyncMock(return_value=routing_decision)
        router.execute_routing = AsyncMock(return_value={"response": "Hello! How can I help?"})
        
        return router
    
    @pytest.fixture
    def mock_session_manager(self):
        """Create mock session manager."""
        manager = Mock()
        
        # Mock session
        session = Mock()
        session.session_id = "test-session"
        session.user_role = "technician"
        session.context = {}
        session.pipeline_session_id = None
        
        manager.get_session = Mock(return_value=session)
        manager.create_session = Mock(return_value=session)
        manager.add_turn = Mock(return_value=True)
        manager.add_error = Mock(return_value=True)
        manager.add_interruption = Mock(return_value=True)
        
        return manager
    
    @pytest.mark.asyncio
    async def test_process_text_input(
        self,
        mock_voice_pipeline,
        mock_agent_router,
        mock_session_manager,
    ):
        """Test processing text input."""
        integration = create_voice_agent_integration(
            voice_pipeline=mock_voice_pipeline,
            agent_router=mock_agent_router,
            session_manager=mock_session_manager,
        )
        
        request = VoiceAgentRequest(
            session_id="test-session",
            text_input="Hello",
        )
        
        response = await integration.process_voice_input(request)
        
        assert response.session_id == "test-session"
        assert response.text_response == "Hello! How can I help?"
        assert response.intent == "greeting"
        assert response.agent_type == "intake"
        assert response.confidence == 0.95
        assert response.mode == InteractionMode.TEXT
    
    @pytest.mark.asyncio
    async def test_handle_interruption(
        self,
        mock_voice_pipeline,
        mock_agent_router,
        mock_session_manager,
    ):
        """Test handling interruption."""
        integration = create_voice_agent_integration(
            voice_pipeline=mock_voice_pipeline,
            agent_router=mock_agent_router,
            session_manager=mock_session_manager,
        )
        
        # Set pipeline session ID
        session = mock_session_manager.get_session("test-session")
        session.pipeline_session_id = "pipeline-session"
        
        handled = await integration.handle_interruption("test-session")
        
        assert handled is True
        mock_voice_pipeline.handle_interruption.assert_called_once()
        mock_session_manager.add_interruption.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_fallback_to_text_mode(
        self,
        mock_voice_pipeline,
        mock_agent_router,
        mock_session_manager,
    ):
        """Test fallback to text mode on error."""
        # Make agent router raise an error
        mock_agent_router.route_request = AsyncMock(side_effect=Exception("Test error"))
        
        integration = create_voice_agent_integration(
            voice_pipeline=mock_voice_pipeline,
            agent_router=mock_agent_router,
            session_manager=mock_session_manager,
        )
        
        request = VoiceAgentRequest(
            session_id="test-session",
            text_input="Hello",
        )
        
        response = await integration.process_voice_input(request)
        
        assert response.mode == InteractionMode.TEXT
        assert response.error is not None
        assert "trouble with voice processing" in response.text_response


# ============================================================================
# Streaming Handler Tests
# ============================================================================


class TestTurnTakingDetector:
    """Test turn-taking detector."""
    
    def test_speech_start(self):
        """Test speech start detection."""
        detector = TurnTakingDetector()
        
        is_interruption = detector.on_speech_start()
        assert is_interruption is False
        assert detector.is_user_speaking is True
    
    def test_interruption_detection(self):
        """Test interruption detection."""
        detector = TurnTakingDetector()
        
        # Agent starts speaking
        detector.on_agent_start()
        assert detector.is_agent_speaking is True
        
        # User interrupts
        is_interruption = detector.on_speech_start()
        assert is_interruption is True
    
    def test_speech_end(self):
        """Test speech end detection."""
        detector = TurnTakingDetector(min_speech_duration_ms=100)
        
        detector.on_speech_start()
        time.sleep(0.15)  # Wait 150ms
        
        turn_complete = detector.on_speech_end()
        assert turn_complete is True
        assert detector.is_user_speaking is False
    
    def test_silence_detection(self):
        """Test silence detection for turn-taking."""
        detector = TurnTakingDetector(silence_threshold_ms=500)
        
        # Short silence - should not end turn
        should_end = detector.on_silence(300)
        assert should_end is False
        
        # Long silence - should end turn
        should_end = detector.on_silence(600)
        assert should_end is True
    
    def test_turn_state(self):
        """Test turn state tracking."""
        detector = TurnTakingDetector()
        
        assert detector.get_turn_state() == "transition"
        
        detector.on_speech_start()
        assert detector.get_turn_state() == "user_turn"
        
        detector.on_speech_end()
        detector.on_agent_start()
        assert detector.get_turn_state() == "agent_turn"


class TestStreamingResponseHandler:
    """Test streaming response handler."""
    
    @pytest.mark.asyncio
    async def test_handler_initialization(self):
        """Test handler is initialized correctly."""
        handler = create_streaming_handler(session_id="test-session")
        
        assert handler.session_id == "test-session"
        assert handler.is_streaming is False
        assert handler.events_processed == 0
    
    @pytest.mark.asyncio
    async def test_start_stop_streaming(self):
        """Test starting and stopping streaming."""
        handler = create_streaming_handler(session_id="test-session")
        
        await handler.start_streaming()
        assert handler.is_streaming is True
        
        await handler.stop_streaming()
        assert handler.is_streaming is False
    
    @pytest.mark.asyncio
    async def test_partial_transcription(self):
        """Test handling partial transcription."""
        handler = create_streaming_handler(session_id="test-session")
        
        event = await handler.handle_partial_transcription(
            text="Hello",
            confidence=0.8,
        )
        
        assert event.event_type == StreamEventType.PARTIAL_TRANSCRIPTION
        assert event.data["text"] == "Hello"
        assert event.data["is_final"] is False
        assert handler.events_processed == 1
    
    @pytest.mark.asyncio
    async def test_final_transcription(self):
        """Test handling final transcription."""
        handler = create_streaming_handler(session_id="test-session")
        
        event = await handler.handle_final_transcription(
            text="Hello world",
            confidence=1.0,
        )
        
        assert event.event_type == StreamEventType.FINAL_TRANSCRIPTION
        assert event.data["text"] == "Hello world"
        assert event.data["is_final"] is True
        assert handler.current_transcription == "Hello world"
    
    @pytest.mark.asyncio
    async def test_speech_start_event(self):
        """Test handling speech start."""
        handler = create_streaming_handler(session_id="test-session")
        
        event = await handler.handle_speech_start()
        
        assert event.event_type == StreamEventType.SPEECH_START
        assert event.data["is_interruption"] is False
    
    @pytest.mark.asyncio
    async def test_interruption_event(self):
        """Test handling interruption."""
        handler = create_streaming_handler(session_id="test-session")
        
        # Start agent speaking
        handler.turn_detector.on_agent_start()
        
        # User interrupts
        event = await handler.handle_speech_start()
        
        assert event.event_type == StreamEventType.INTERRUPTION
        assert event.data["is_interruption"] is True
        assert handler.interruptions_detected == 1
    
    @pytest.mark.asyncio
    async def test_agent_response_streaming(self):
        """Test streaming agent responses."""
        handler = create_streaming_handler(session_id="test-session")
        
        # Start response
        start_event = await handler.handle_agent_response_start()
        assert start_event.event_type == StreamEventType.AGENT_RESPONSE_START
        
        # Stream chunks
        chunk_event = await handler.handle_agent_response_chunk(
            text="Hello",
            audio_chunk=b"audio_data",
        )
        assert chunk_event.event_type == StreamEventType.AGENT_RESPONSE_CHUNK
        assert chunk_event.data["text"] == "Hello"
        assert chunk_event.data["has_audio"] is True
        
        # End response
        end_event = await handler.handle_agent_response_end()
        assert end_event.event_type == StreamEventType.AGENT_RESPONSE_END
    
    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """Test getting streaming metrics."""
        handler = create_streaming_handler(session_id="test-session")
        
        await handler.handle_partial_transcription("Hello")
        await handler.handle_speech_start()
        
        metrics = handler.get_metrics()
        assert metrics["session_id"] == "test-session"
        assert metrics["events_processed"] == 2
        assert metrics["interruptions_detected"] == 0


# ============================================================================
# Integration Tests
# ============================================================================


class TestVoiceAgentEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_complete_voice_interaction_flow(self):
        """Test complete voice-to-agent-to-speech flow."""
        # This would test the complete flow:
        # 1. Create session
        # 2. Process voice input
        # 3. Route to agent
        # 4. Generate response
        # 5. Synthesize speech
        # 6. Track metrics
        
        # TODO: Implement with real components
        pass
    
    @pytest.mark.asyncio
    async def test_streaming_with_interruption(self):
        """Test streaming interaction with interruption."""
        # This would test:
        # 1. Start streaming session
        # 2. Stream partial transcriptions
        # 3. Detect interruption
        # 4. Handle interruption gracefully
        # 5. Resume interaction
        
        # TODO: Implement with real components
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
