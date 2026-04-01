"""
Tests for Azure Speech Voice Activity Detection (VAD)
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
import time
from voice.vad import (
    AzureSpeechVAD,
    VADConfig,
    VADState,
    create_azure_vad,
)


def test_vad_initialization():
    """Test VAD initialization with default config."""
    vad = create_azure_vad()
    
    assert vad is not None
    assert vad.config.sensitivity == 0.5
    assert vad.config.adaptive_threshold is True
    assert vad.current_state == VADState.SILENCE


def test_vad_custom_config():
    """Test VAD initialization with custom config."""
    config = VADConfig(
        sensitivity=0.7,
        min_speech_duration_ms=200,
        min_silence_duration_ms=300,
        adaptive_threshold=False,
    )
    
    vad = AzureSpeechVAD(config=config)
    
    assert vad.config.sensitivity == 0.7
    assert vad.config.min_speech_duration_ms == 200
    assert vad.config.min_silence_duration_ms == 300
    assert vad.config.adaptive_threshold is False


def test_vad_speech_detection():
    """Test basic speech detection."""
    speech_started = []
    speech_ended = []
    
    def on_start(timestamp):
        speech_started.append(timestamp)
    
    def on_end(timestamp):
        speech_ended.append(timestamp)
    
    vad = create_azure_vad(
        sensitivity=0.5,
        on_speech_start=on_start,
        on_speech_end=on_end,
    )
    
    # Simulate audio levels
    timestamp = 0.0
    
    # Silence
    state = vad.process_audio_level(0.3, timestamp)
    assert state == VADState.SILENCE
    
    # Speech starts (above threshold)
    timestamp += 0.05
    state = vad.process_audio_level(0.8, timestamp)
    assert state in [VADState.UNCERTAIN, VADState.SPEECH]
    
    # Continue speech
    timestamp += 0.15
    state = vad.process_audio_level(0.9, timestamp)
    assert state == VADState.SPEECH
    assert len(speech_started) == 1
    
    # Speech continues
    timestamp += 0.1
    state = vad.process_audio_level(0.7, timestamp)
    assert state == VADState.SPEECH
    
    # Silence starts
    timestamp += 0.1
    state = vad.process_audio_level(0.2, timestamp)
    assert state == VADState.SPEECH  # Still speech (min silence not met)
    
    # Silence continues (min silence duration met)
    timestamp += 0.6
    state = vad.process_audio_level(0.1, timestamp)
    assert state == VADState.SILENCE
    assert len(speech_ended) == 1


def test_vad_adaptive_threshold():
    """Test adaptive threshold for noisy environments."""
    vad = create_azure_vad(sensitivity=0.5, adaptive=True)
    
    # Normal noise level
    vad.update_ambient_noise(50.0)
    threshold1 = vad.get_adaptive_threshold()
    assert threshold1 == 0.5
    
    # High noise level (exceeds 60dB threshold)
    vad.update_ambient_noise(70.0)
    vad.update_ambient_noise(75.0)
    threshold2 = vad.get_adaptive_threshold()
    assert threshold2 > 0.5  # Increased sensitivity
    assert threshold2 <= 1.0


def test_vad_speech_boundary_detection():
    """Test speech boundary detection with minimum duration."""
    speech_started = []
    
    def on_start(timestamp):
        speech_started.append(timestamp)
    
    config = VADConfig(
        sensitivity=0.5,
        min_speech_duration_ms=100,
        boundary_detection=True,
    )
    
    vad = AzureSpeechVAD(config=config, on_speech_start=on_start)
    
    timestamp = 0.0
    
    # Very short speech burst (< 100ms)
    state = vad.process_audio_level(0.8, timestamp)
    assert state == VADState.UNCERTAIN
    
    timestamp += 0.05  # 50ms later
    state = vad.process_audio_level(0.2, timestamp)  # Back to silence
    assert state == VADState.SILENCE  # False alarm
    assert len(speech_started) == 0  # No speech start callback
    
    # Longer speech (> 100ms)
    timestamp += 0.1
    state = vad.process_audio_level(0.9, timestamp)
    assert state == VADState.UNCERTAIN
    
    timestamp += 0.15  # 150ms later
    state = vad.process_audio_level(0.8, timestamp)
    assert state == VADState.SPEECH  # Confirmed
    assert len(speech_started) == 1


def test_vad_reset():
    """Test VAD state reset."""
    # Disable boundary detection for simpler testing
    config = VADConfig(boundary_detection=False)
    vad = AzureSpeechVAD(config=config)
    
    # Trigger speech
    vad.process_audio_level(0.9, 0.0)
    vad.process_audio_level(0.9, 0.2)
    assert vad.current_state == VADState.SPEECH
    
    # Reset
    vad.reset()
    assert vad.current_state == VADState.SILENCE
    assert vad.speech_start_time is None
    assert vad.silence_start_time is None


def test_vad_speech_duration():
    """Test speech duration calculation."""
    # Disable boundary detection for simpler testing
    config = VADConfig(boundary_detection=False)
    vad = AzureSpeechVAD(config=config)
    
    # No active speech
    duration = vad.get_speech_duration(1.0)
    assert duration is None
    
    # Start speech
    vad.process_audio_level(0.9, 0.0)
    print(f"After first call: state={vad.current_state}, speech_start_time={vad.speech_start_time}")
    assert vad.current_state == VADState.SPEECH
    
    # Check duration immediately after speech starts
    duration = vad.get_speech_duration(0.0)
    print(f"Duration at 0.0: {duration}")
    assert duration is not None
    assert duration == 0.0
    
    # Continue speech
    vad.process_audio_level(0.9, 0.15)
    print(f"After second call: state={vad.current_state}, speech_start_time={vad.speech_start_time}")
    assert vad.current_state == VADState.SPEECH
    
    # Check duration at a later time
    duration = vad.get_speech_duration(0.5)
    print(f"Duration at 0.5: {duration}")
    assert duration is not None
    assert duration == 0.5  # 0.5 - 0.0 (speech_start_time)


def test_vad_is_speech_active():
    """Test speech activity check."""
    # Disable boundary detection for simpler testing
    config = VADConfig(boundary_detection=False)
    vad = AzureSpeechVAD(config=config)
    
    assert not vad.is_speech_active()
    
    # Trigger speech
    vad.process_audio_level(0.9, 0.0)
    vad.process_audio_level(0.9, 0.15)
    
    assert vad.is_speech_active()
    
    # End speech
    vad.process_audio_level(0.1, 0.3)
    vad.process_audio_level(0.1, 0.9)
    
    assert not vad.is_speech_active()


def test_vad_ambient_noise_tracking():
    """Test ambient noise level tracking."""
    vad = create_azure_vad()
    
    # Add noise samples
    vad.update_ambient_noise(50.0)
    vad.update_ambient_noise(55.0)
    vad.update_ambient_noise(52.0)
    
    # Check average
    assert 50.0 <= vad.ambient_noise_level <= 55.0
    
    # Add many samples (test max samples limit)
    for i in range(150):
        vad.update_ambient_noise(60.0 + i * 0.1)
    
    # Should only keep last 100 samples
    assert len(vad.noise_samples) == vad.max_noise_samples


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
