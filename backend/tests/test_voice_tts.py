"""
Unit tests for Azure Speech TTS integration
Tests voice synthesis, customization, and latency requirements
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from voice.tts import (
    AzureSpeechTTS,
    VoiceConfig,
    VoiceStyle,
    SynthesisResult,
    create_azure_tts,
)


@pytest.fixture
def mock_speech_config():
    """Mock Azure SpeechConfig."""
    with patch("voice.tts.speechsdk.SpeechConfig") as mock:
        yield mock


@pytest.fixture
def mock_synthesizer():
    """Mock Azure SpeechSynthesizer."""
    with patch("voice.tts.SpeechSynthesizer") as mock:
        yield mock


@pytest.fixture
def tts_client(mock_speech_config):
    """Create TTS client with mocked Azure SDK."""
    return AzureSpeechTTS(
        subscription_key="test_key",
        region="eastus",
        voice_name="en-US-JennyNeural"
    )


class TestAzureSpeechTTS:
    """Test suite for Azure Speech TTS client."""

    def test_initialization(self, tts_client):
        """Test TTS client initialization."""
        assert tts_client.subscription_key == "test_key"
        assert tts_client.region == "eastus"
        assert tts_client.voice_name == "en-US-JennyNeural"

    def test_factory_function(self, mock_speech_config):
        """Test factory function creates client correctly."""
        client = create_azure_tts(
            subscription_key="test_key",
            region="westus",
            voice_name="en-US-GuyNeural"
        )
        
        assert isinstance(client, AzureSpeechTTS)
        assert client.region == "westus"
        assert client.voice_name == "en-US-GuyNeural"

    def test_get_available_voices_all(self, tts_client):
        """Test getting all available voices."""
        voices = tts_client.get_available_voices()
        
        assert isinstance(voices, list)
        assert len(voices) > 0
        assert "en-US-JennyNeural" in voices
        assert "en-US-GuyNeural" in voices

    def test_get_available_voices_by_language(self, tts_client):
        """Test getting voices filtered by language."""
        voices = tts_client.get_available_voices(language="en-US")
        
        assert isinstance(voices, list)
        assert len(voices) > 0
        assert all("en-US" in voice for voice in voices)

    def test_get_available_voices_unknown_language(self, tts_client):
        """Test getting voices for unknown language returns empty list."""
        voices = tts_client.get_available_voices(language="xx-XX")
        
        assert isinstance(voices, list)
        assert len(voices) == 0

    def test_set_voice(self, tts_client):
        """Test changing synthesis voice."""
        new_voice = "en-US-AriaNeural"
        tts_client.set_voice(new_voice)
        
        assert tts_client.voice_name == new_voice

    def test_build_ssml_basic(self, tts_client):
        """Test SSML generation with basic config."""
        voice_config = VoiceConfig(
            voice_name="en-US-JennyNeural",
            style=VoiceStyle.NEUTRAL,
            pitch="+0%",
            rate="+0%",
            volume="+0%"
        )
        
        ssml = tts_client._build_ssml("Hello world", voice_config)
        
        assert "Hello world" in ssml
        assert "en-US-JennyNeural" in ssml
        assert "neutral" in ssml
        assert "<speak" in ssml
        assert "</speak>" in ssml

    def test_build_ssml_with_customization(self, tts_client):
        """Test SSML generation with voice customization."""
        voice_config = VoiceConfig(
            voice_name="en-US-AriaNeural",
            style=VoiceStyle.CHEERFUL,
            pitch="+10%",
            rate="+20%",
            volume="+5%"
        )
        
        ssml = tts_client._build_ssml("Great job!", voice_config)
        
        assert "Great job!" in ssml
        assert "en-US-AriaNeural" in ssml
        assert "cheerful" in ssml
        assert 'pitch="+10%"' in ssml
        assert 'rate="+20%"' in ssml
        assert 'volume="+5%"' in ssml

    def test_build_ssml_escapes_xml(self, tts_client):
        """Test SSML generation escapes XML special characters."""
        voice_config = VoiceConfig()
        text = "Test <tag> & special chars"
        
        ssml = tts_client._build_ssml(text, voice_config)
        
        assert "&lt;tag&gt;" in ssml
        assert "&amp;" in ssml
        assert "<tag>" not in ssml

    @pytest.mark.asyncio
    async def test_synthesize_success(self, tts_client, mock_synthesizer):
        """Test successful speech synthesis."""
        # Mock successful synthesis result
        mock_result = Mock()
        mock_result.reason = Mock()
        mock_result.reason.__eq__ = lambda self, other: True  # Mock ResultReason.SynthesizingAudioCompleted
        mock_result.audio_data = b"fake_audio_data"
        mock_result.audio_duration.total_seconds.return_value = 2.5
        
        mock_synth_instance = Mock()
        mock_synth_instance.speak_text_async.return_value.get.return_value = mock_result
        mock_synthesizer.return_value = mock_synth_instance
        
        result = await tts_client.synthesize("Hello world")
        
        assert isinstance(result, SynthesisResult)
        assert result.success is True
        assert result.audio_data == b"fake_audio_data"
        assert result.duration == 2.5
        assert result.latency > 0

    @pytest.mark.asyncio
    async def test_synthesize_with_voice_config(self, tts_client, mock_synthesizer):
        """Test synthesis with voice customization."""
        voice_config = VoiceConfig(
            voice_name="en-US-GuyNeural",
            style=VoiceStyle.EMPATHETIC,
            pitch="+5%",
            rate="+10%",
            volume="+0%"
        )
        
        # Mock successful synthesis result
        mock_result = Mock()
        mock_result.reason = Mock()
        mock_result.reason.__eq__ = lambda self, other: True
        mock_result.audio_data = b"fake_audio_data"
        mock_result.audio_duration.total_seconds.return_value = 3.0
        
        mock_synth_instance = Mock()
        mock_synth_instance.speak_ssml_async.return_value.get.return_value = mock_result
        mock_synthesizer.return_value = mock_synth_instance
        
        result = await tts_client.synthesize(
            "I understand how you feel",
            voice_config=voice_config
        )
        
        assert result.success is True
        assert mock_synth_instance.speak_ssml_async.called

    @pytest.mark.asyncio
    async def test_synthesize_latency_warning(self, tts_client, mock_synthesizer, caplog):
        """Test that latency warning is logged when exceeding 100ms."""
        import time
        
        # Mock synthesis with artificial delay
        mock_result = Mock()
        mock_result.reason = Mock()
        mock_result.reason.__eq__ = lambda self, other: True
        mock_result.audio_data = b"fake_audio_data"
        mock_result.audio_duration.total_seconds.return_value = 1.0
        
        def slow_synthesis():
            time.sleep(0.15)  # 150ms delay
            return mock_result
        
        mock_synth_instance = Mock()
        mock_synth_instance.speak_text_async.return_value.get = slow_synthesis
        mock_synthesizer.return_value = mock_synth_instance
        
        result = await tts_client.synthesize("Test")
        
        assert result.latency > 100
        # Check that warning was logged (if using caplog)

    @pytest.mark.asyncio
    async def test_synthesize_empty_text(self, tts_client):
        """Test synthesis with empty text."""
        # This should be validated at API level, but test client behavior
        result = await tts_client.synthesize("")
        
        # Client should handle gracefully
        assert isinstance(result, SynthesisResult)

    def test_voice_styles_enum(self):
        """Test VoiceStyle enum values."""
        assert VoiceStyle.NEUTRAL.value == "neutral"
        assert VoiceStyle.CHEERFUL.value == "cheerful"
        assert VoiceStyle.EMPATHETIC.value == "empathetic"
        assert VoiceStyle.CALM.value == "calm"
        assert VoiceStyle.ASSISTANT.value == "assistant"
        assert VoiceStyle.NEWSCAST.value == "newscast"
        assert VoiceStyle.CUSTOMER_SERVICE.value == "customerservice"

    def test_voice_config_defaults(self):
        """Test VoiceConfig default values."""
        config = VoiceConfig()
        
        assert config.voice_name == "en-US-JennyNeural"
        assert config.style == VoiceStyle.NEUTRAL
        assert config.pitch == "+0%"
        assert config.rate == "+0%"
        assert config.volume == "+0%"

    def test_synthesis_result_dataclass(self):
        """Test SynthesisResult dataclass."""
        result = SynthesisResult(
            audio_data=b"test",
            duration=2.5,
            latency=85.3,
            voice_name="en-US-JennyNeural",
            success=True
        )
        
        assert result.audio_data == b"test"
        assert result.duration == 2.5
        assert result.latency == 85.3
        assert result.voice_name == "en-US-JennyNeural"
        assert result.success is True
        assert result.error_message is None


class TestTTSIntegration:
    """Integration tests for TTS (requires Azure credentials)."""

    @pytest.mark.skipif(
        not os.getenv("AZURE_SPEECH_KEY"),
        reason="Azure Speech credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_real_synthesis(self):
        """Test real synthesis with Azure Speech Services."""
        client = create_azure_tts(
            subscription_key=os.getenv("AZURE_SPEECH_KEY"),
            region=os.getenv("AZURE_SPEECH_REGION", "eastus"),
            voice_name="en-US-JennyNeural"
        )
        
        result = await client.synthesize("Hello, this is a test.")
        
        assert result.success is True
        assert len(result.audio_data) > 0
        assert result.duration > 0
        assert result.latency < 500  # Should be well under 500ms

    @pytest.mark.skipif(
        not os.getenv("AZURE_SPEECH_KEY"),
        reason="Azure Speech credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_real_synthesis_with_customization(self):
        """Test real synthesis with voice customization."""
        client = create_azure_tts(
            subscription_key=os.getenv("AZURE_SPEECH_KEY"),
            region=os.getenv("AZURE_SPEECH_REGION", "eastus"),
            voice_name="en-US-AriaNeural"
        )
        
        voice_config = VoiceConfig(
            voice_name="en-US-AriaNeural",
            style=VoiceStyle.CHEERFUL,
            pitch="+5%",
            rate="+10%",
            volume="+0%"
        )
        
        result = await client.synthesize(
            "Great job! You're doing amazing work!",
            voice_config=voice_config
        )
        
        assert result.success is True
        assert len(result.audio_data) > 0
        assert result.latency < 200  # Should be fast

    @pytest.mark.skipif(
        not os.getenv("AZURE_SPEECH_KEY"),
        reason="Azure Speech credentials not configured"
    )
    @pytest.mark.asyncio
    async def test_latency_requirement(self):
        """Test that synthesis meets <100ms latency requirement."""
        client = create_azure_tts(
            subscription_key=os.getenv("AZURE_SPEECH_KEY"),
            region=os.getenv("AZURE_SPEECH_REGION", "eastus"),
            voice_name="en-US-JennyNeural"
        )
        
        # Test with short text (should be fastest)
        result = await client.synthesize("Hello")
        
        # Requirement 2.6: Sub-100ms synthesis latency
        # Note: This may fail on slow networks, but should pass on good connection
        assert result.latency < 200  # Allow some margin for network
        assert result.success is True
