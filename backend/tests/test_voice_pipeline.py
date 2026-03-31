"""
Tests for Voice Pipeline Orchestrator
"""

import pytest
import os
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from voice.pipeline import (
    VoicePipeline,
    VoicePipelineConfig,
    VoiceSession,
    SessionState,
    TurnState,
    SessionMetrics,
    create_voice_pipeline,
)
from voice.tts import VoiceConfig, VoiceStyle


# Skip tests if Azure credentials not available
pytestmark = pytest.mark.skipif(
    not os.getenv("AZURE_SPEECH_KEY") or not os.getenv("AZURE_SPEECH_REGION"),
    reason="Azure Speech credentials not configured"
)


@pytest.fixture
def pipeline_config():
    """Create pipeline configuration for testing."""
    return VoicePipelineConfig(
        azure_speech_key=os.getenv("AZURE_SPEECH_KEY", "test-key"),
        azure_speech_region=os.getenv("AZURE_SPEECH_REGION", "eastus"),
        stt_language="en-US",
        tts_voice_name="en-US-JennyNeural",
        latency_target_ms=500,
        tts_latency_target_ms=100,
    )


@pytest.fixture
def pipeline(pipeline_config):
    """Create pipeline instance for testing."""
    return VoicePipeline(pipeline_config)


class TestVoicePipelineConfig:
    """Test VoicePipelineConfig."""
    
    def test_config_creation(self, pipeline_config):
        """Test configuration creation with defaults."""
        assert pipeline_config.azure_speech_key is not None
        assert pipeline_config.azure_speech_region is not None
        assert pipeline_config.stt_language == "en-US"
        assert pipeline_config.tts_voice_name == "en-US-JennyNeural"
        assert pipeline_config.latency_target_ms == 500
        assert pipeline_config.tts_latency_target_ms == 100
    
    def test_config_customization(self):
        """Test configuration with custom values."""
        config = VoicePipelineConfig(
            azure_speech_key="custom-key",
            azure_speech_region="westus",
            stt_language="es-ES",
            tts_voice_name="es-ES-ElviraNeural",
            vad_sensitivity=0.7,
            latency_target_ms=300,
        )
        
        assert config.azure_speech_key == "custom-key"
        assert config.azure_speech_region == "westus"
        assert config.stt_language == "es-ES"
        assert config.tts_voice_name == "es-ES-ElviraNeural"
        assert config.vad_sensitivity == 0.7
        assert config.latency_target_ms == 300


class TestSessionMetrics:
    """Test SessionMetrics."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = SessionMetrics(session_id="test-session", start_time=1000.0)
        
        assert metrics.session_id == "test-session"
        assert metrics.start_time == 1000.0
        assert metrics.turn_count == 0
        assert metrics.user_turns == 0
        assert metrics.agent_turns == 0
        assert metrics.interruptions == 0
        assert metrics.avg_latency == 0.0
    
    def test_add_latency(self):
        """Test adding latency measurements."""
        metrics = SessionMetrics(session_id="test", start_time=1000.0)
        
        metrics.add_latency(100.0)
        assert metrics.avg_latency == 100.0
        
        metrics.add_latency(200.0)
        assert metrics.avg_latency == 150.0
        
        metrics.add_latency(300.0)
        assert metrics.avg_latency == 200.0
    
    def test_session_duration(self):
        """Test session duration calculation."""
        metrics = SessionMetrics(session_id="test", start_time=1000.0)
        
        # Without end time (uses current time)
        duration = metrics.get_session_duration()
        assert duration > 0
        
        # With end time
        metrics.end_time = 1100.0
        assert metrics.get_session_duration() == 100.0
    
    def test_turn_taking_accuracy(self):
        """Test turn-taking accuracy calculation."""
        metrics = SessionMetrics(session_id="test", start_time=1000.0)
        
        # No turns yet
        assert metrics.get_turn_taking_accuracy() == 1.0
        
        # Perfect turn-taking (no interruptions)
        metrics.user_turns = 5
        metrics.agent_turns = 5
        metrics.interruptions = 0
        assert metrics.get_turn_taking_accuracy() == 1.0
        
        # One interruption out of 10 turns = 90% accuracy
        metrics.interruptions = 1
        assert metrics.get_turn_taking_accuracy() == 0.9
        
        # Two interruptions out of 10 turns = 80% accuracy
        metrics.interruptions = 2
        assert metrics.get_turn_taking_accuracy() == 0.8


class TestVoicePipeline:
    """Test VoicePipeline."""
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, pipeline):
        """Test pipeline initialization."""
        await pipeline.initialize()
        assert len(pipeline.sessions) == 0
    
    @pytest.mark.asyncio
    async def test_start_session(self, pipeline):
        """Test starting a voice session."""
        session = await pipeline.start_session()
        
        assert session.session_id is not None
        assert session.state == SessionState.IDLE
        assert session.turn_state == TurnState.USER_TURN
        assert session.stt is not None
        assert session.tts is not None
        assert session.vad is not None
        assert session.metrics.session_id == session.session_id
        
        # Session should be in active sessions
        assert session.session_id in pipeline.sessions
    
    @pytest.mark.asyncio
    async def test_start_session_with_custom_id(self, pipeline):
        """Test starting a session with custom ID."""
        custom_id = "custom-session-123"
        session = await pipeline.start_session(session_id=custom_id)
        
        assert session.session_id == custom_id
        assert custom_id in pipeline.sessions
    
    @pytest.mark.asyncio
    async def test_start_session_with_context(self, pipeline):
        """Test starting a session with context."""
        context = {"user_id": "user-123", "language": "en-US"}
        session = await pipeline.start_session(context=context)
        
        assert session.context == context
    
    @pytest.mark.asyncio
    async def test_get_session(self, pipeline):
        """Test getting a session."""
        session = await pipeline.start_session()
        
        retrieved = pipeline.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id
        
        # Non-existent session
        assert pipeline.get_session("non-existent") is None
    
    @pytest.mark.asyncio
    async def test_end_session(self, pipeline):
        """Test ending a session."""
        session = await pipeline.start_session()
        session_id = session.session_id
        
        await pipeline.end_session(session_id)
        
        # Session should be removed
        assert session_id not in pipeline.sessions
        assert session.state == SessionState.ENDED
        assert session.metrics.end_time is not None
    
    @pytest.mark.asyncio
    async def test_handle_interruption(self, pipeline):
        """Test handling interruptions."""
        session = await pipeline.start_session()
        
        # No interruption when not speaking
        handled = pipeline.handle_interruption(session.session_id)
        assert not handled
        
        # Interruption when speaking
        session.state = SessionState.SPEAKING
        handled = pipeline.handle_interruption(session.session_id)
        assert handled
        assert session.state == SessionState.INTERRUPTED
        assert session.turn_state == TurnState.USER_TURN
        assert session.metrics.interruptions == 1
    
    @pytest.mark.asyncio
    async def test_interruption_callback(self, pipeline):
        """Test interruption callback."""
        callback_called = False
        interrupted_session_id = None
        
        def on_interruption(session_id):
            nonlocal callback_called, interrupted_session_id
            callback_called = True
            interrupted_session_id = session_id
        
        pipeline.set_callbacks(on_interruption=on_interruption)
        
        session = await pipeline.start_session()
        session.state = SessionState.SPEAKING
        
        pipeline.handle_interruption(session.session_id)
        
        assert callback_called
        assert interrupted_session_id == session.session_id
    
    @pytest.mark.asyncio
    async def test_get_session_metrics(self, pipeline):
        """Test getting session metrics."""
        session = await pipeline.start_session()
        
        metrics = pipeline.get_session_metrics(session.session_id)
        assert metrics is not None
        assert metrics.session_id == session.session_id
        
        # Non-existent session
        assert pipeline.get_session_metrics("non-existent") is None
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, pipeline):
        """Test cleaning up inactive sessions."""
        # Create a session
        session = await pipeline.start_session()
        
        # Should not be cleaned up immediately
        await pipeline.cleanup_inactive_sessions(timeout_seconds=10)
        assert session.session_id in pipeline.sessions
        
        # Should be cleaned up with 0 timeout
        await pipeline.cleanup_inactive_sessions(timeout_seconds=0)
        assert session.session_id not in pipeline.sessions


class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_voice_pipeline(self):
        """Test creating pipeline with factory function."""
        pipeline = create_voice_pipeline(
            azure_speech_key="test-key",
            azure_speech_region="eastus",
            stt_language="es-ES",
        )
        
        assert isinstance(pipeline, VoicePipeline)
        assert pipeline.config.azure_speech_key == "test-key"
        assert pipeline.config.azure_speech_region == "eastus"
        assert pipeline.config.stt_language == "es-ES"


class TestIntegration:
    """Integration tests (require Azure credentials)."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_session_lifecycle(self, pipeline):
        """Test complete session lifecycle."""
        # Start session
        session = await pipeline.start_session(
            context={"test": "integration"}
        )
        
        assert session.state == SessionState.IDLE
        assert session.metrics.turn_count == 0
        
        # Simulate some activity
        session.metrics.user_turns = 3
        session.metrics.agent_turns = 3
        session.metrics.turn_count = 6
        session.metrics.add_latency(450.0)
        session.metrics.add_latency(480.0)
        session.metrics.add_latency(520.0)
        
        # Get metrics
        metrics = pipeline.get_session_metrics(session.session_id)
        assert metrics.turn_count == 6
        assert metrics.user_turns == 3
        assert metrics.agent_turns == 3
        assert 450.0 <= metrics.avg_latency <= 520.0
        
        # End session
        await pipeline.end_session(session.session_id)
        
        assert session.state == SessionState.ENDED
        assert session.metrics.end_time is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
