"""Voice processing module for TradeSense."""

from .stt import AzureSpeechSTT, TranscriptionResult, TranscriptionChunk, create_azure_stt
from .tts import AzureSpeechTTS, VoiceConfig, VoiceStyle, SynthesisResult, create_azure_tts
from .vad import AzureSpeechVAD, VADConfig, VADState, create_azure_vad

__all__ = [
    # STT
    "AzureSpeechSTT",
    "TranscriptionResult",
    "TranscriptionChunk",
    "create_azure_stt",
    # TTS
    "AzureSpeechTTS",
    "VoiceConfig",
    "VoiceStyle",
    "SynthesisResult",
    "create_azure_tts",
    # VAD
    "AzureSpeechVAD",
    "VADConfig",
    "VADState",
    "create_azure_vad",
]
