"""
Unit tests for Azure Speech Services STT integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import azure.cognitiveservices.speech as speechsdk

from voice.stt import AzureSpeechSTT, TranscriptionResult, TranscriptionChunk, create_azure_stt


class TestAzureSpeechSTT:
    """Test suite for AzureSpeechSTT class."""

    @pytest.fixture
    def stt_client(self):
        """Create a test STT client."""
        return AzureSpeechSTT(
            subscription_key="test_key",
            region="eastus",
            language="en-US"
        )

    def test_initialization(self, stt_client):
        """Test STT client initialization."""
        assert stt_client.subscription_key == "test_key"
        assert stt_client.region == "eastus"
        assert stt_client.language == "en-US"
        assert stt_client.speech_config is not None

    def test_supported_languages(self, stt_client):
        """Test getting supported languages."""
        languages = stt_client.get_supported_languages()
        assert isinstance(languages, list)
        assert len(languages) > 0
        assert "en-US" in languages
        assert "es-ES" in languages
        assert "fr-FR" in languages

    def test_set_language(self, stt_client):
        """Test changing recognition language."""
        stt_client.set_language("es-ES")
        assert stt_client.language == "es-ES"
        assert stt_client.speech_config.speech_recognition_language == "es-ES"

    def test_create_recognizer(self, stt_client):
        """Test creating a speech recognizer."""
        recognizer = stt_client.create_recognizer()
        assert recognizer is not None
        assert isinstance(recognizer, speechsdk.SpeechRecognizer)

    def test_create_audio_config_from_file(self):
        """Test creating audio config from file."""
        audio_config = AzureSpeechSTT.create_audio_config_from_file("test.wav")
        assert audio_config is not None
        assert isinstance(audio_config, speechsdk.audio.AudioConfig)

    def test_factory_function(self):
        """Test factory function for creating STT client."""
        client = create_azure_stt(
            subscription_key="test_key",
            region="westus",
            language="en-GB"
        )
        assert isinstance(client, AzureSpeechSTT)
        assert client.subscription_key == "test_key"
        assert client.region == "westus"
        assert client.language == "en-GB"

    @pytest.mark.asyncio
    async def test_transcribe_once_success(self, stt_client):
        """Test single-shot transcription with successful result."""
        # Mock the recognizer and result
        mock_result = Mock()
        mock_result.reason = speechsdk.ResultReason.RecognizedSpeech
        mock_result.text = "Hello world"
        mock_result.duration = Mock(total_seconds=lambda: 2.5)
        
        with patch.object(stt_client, 'create_recognizer') as mock_create:
            mock_recognizer = Mock()
            mock_recognizer.recognize_once.return_value = mock_result
            mock_create.return_value = mock_recognizer
            
            result = await stt_client.transcribe_once()
            
            assert isinstance(result, TranscriptionResult)
            assert result.text == "Hello world"
            assert result.duration == 2.5
            assert len(result.chunks) == 1
            assert result.chunks[0].text == "Hello world"
            assert result.chunks[0].is_final is True

    @pytest.mark.asyncio
    async def test_transcribe_once_no_match(self, stt_client):
        """Test single-shot transcription with no speech detected."""
        mock_result = Mock()
        mock_result.reason = speechsdk.ResultReason.NoMatch
        
        with patch.object(stt_client, 'create_recognizer') as mock_create:
            mock_recognizer = Mock()
            mock_recognizer.recognize_once.return_value = mock_result
            mock_create.return_value = mock_recognizer
            
            result = await stt_client.transcribe_once()
            
            assert result.text == ""
            assert result.confidence == 0.0
            assert len(result.chunks) == 0

    @pytest.mark.asyncio
    async def test_transcribe_once_canceled(self, stt_client):
        """Test single-shot transcription with cancellation."""
        mock_result = Mock()
        mock_result.reason = speechsdk.ResultReason.Canceled
        mock_cancellation = Mock()
        mock_cancellation.reason = speechsdk.CancellationReason.Error
        mock_cancellation.error_details = "Test error"
        mock_result.cancellation_details = mock_cancellation
        
        with patch.object(stt_client, 'create_recognizer') as mock_create:
            mock_recognizer = Mock()
            mock_recognizer.recognize_once.return_value = mock_result
            mock_create.return_value = mock_recognizer
            
            with pytest.raises(RuntimeError, match="Recognition canceled"):
                await stt_client.transcribe_once()

    @pytest.mark.asyncio
    async def test_transcribe_stream(self, stt_client):
        """Test streaming transcription setup."""
        callback_recognizing = Mock()
        callback_recognized = Mock()
        callback_canceled = Mock()
        
        with patch.object(stt_client, 'create_recognizer') as mock_create:
            mock_recognizer = Mock()
            mock_create.return_value = mock_recognizer
            
            recognizer = await stt_client.transcribe_stream(
                callback_recognizing=callback_recognizing,
                callback_recognized=callback_recognized,
                callback_canceled=callback_canceled
            )
            
            assert recognizer is not None
            mock_recognizer.recognizing.connect.assert_called_once_with(callback_recognizing)
            mock_recognizer.recognized.connect.assert_called_once_with(callback_recognized)
            mock_recognizer.canceled.connect.assert_called_once_with(callback_canceled)
            mock_recognizer.start_continuous_recognition.assert_called_once()

    def test_stop_recognition(self, stt_client):
        """Test stopping continuous recognition."""
        mock_recognizer = Mock()
        stt_client.stop_recognition(mock_recognizer)
        mock_recognizer.stop_continuous_recognition.assert_called_once()


class TestTranscriptionModels:
    """Test suite for transcription data models."""

    def test_transcription_chunk(self):
        """Test TranscriptionChunk dataclass."""
        chunk = TranscriptionChunk(
            text="Hello",
            confidence=0.95,
            is_final=False,
            timestamp=1.5,
            duration=0.5
        )
        assert chunk.text == "Hello"
        assert chunk.confidence == 0.95
        assert chunk.is_final is False
        assert chunk.timestamp == 1.5
        assert chunk.duration == 0.5

    def test_transcription_result(self):
        """Test TranscriptionResult dataclass."""
        chunks = [
            TranscriptionChunk("Hello", 0.9, False, 0.0, 0.5),
            TranscriptionChunk("world", 0.95, True, 0.5, 0.5)
        ]
        result = TranscriptionResult(
            text="Hello world",
            confidence=0.92,
            duration=1.0,
            chunks=chunks
        )
        assert result.text == "Hello world"
        assert result.confidence == 0.92
        assert result.duration == 1.0
        assert len(result.chunks) == 2
        assert result.chunks[0].text == "Hello"
        assert result.chunks[1].text == "world"
