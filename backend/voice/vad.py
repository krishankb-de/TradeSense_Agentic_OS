"""
Azure Speech Voice Activity Detection (VAD)
Implements adaptive VAD using Azure Speech SDK's built-in capabilities
"""

import logging
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class VADState(Enum):
    """Voice activity detection states."""
    SILENCE = "silence"
    SPEECH = "speech"
    UNCERTAIN = "uncertain"


@dataclass
class VADConfig:
    """Configuration for Voice Activity Detection."""
    # Sensitivity level (0.0 = least sensitive, 1.0 = most sensitive)
    sensitivity: float = 0.5
    
    # Minimum speech duration in milliseconds
    min_speech_duration_ms: int = 100
    
    # Minimum silence duration in milliseconds to consider speech ended
    min_silence_duration_ms: int = 500
    
    # Adaptive threshold for noisy environments
    adaptive_threshold: bool = True
    
    # Noise level threshold in dB (for adaptive mode)
    noise_threshold_db: float = 60.0
    
    # Speech boundary detection enabled
    boundary_detection: bool = True


class AzureSpeechVAD:
    """
    Voice Activity Detection using Azure Speech SDK.
    
    Azure Speech SDK has built-in VAD capabilities that we leverage:
    - Automatic speech detection
    - Silence detection
    - Speech boundary detection
    - Adaptive threshold for noisy environments
    """
    
    def __init__(
        self,
        config: Optional[VADConfig] = None,
        on_speech_start: Optional[Callable] = None,
        on_speech_end: Optional[Callable] = None,
    ):
        """
        Initialize Azure Speech VAD.
        
        Args:
            config: VAD configuration
            on_speech_start: Callback when speech starts
            on_speech_end: Callback when speech ends
        """
        self.config = config or VADConfig()
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        
        self.current_state = VADState.SILENCE
        self.speech_start_time: Optional[float] = None
        self.silence_start_time: Optional[float] = None
        
        # Adaptive threshold tracking
        self.ambient_noise_level: float = 0.0
        self.noise_samples: list = []
        self.max_noise_samples = 100
        
        logger.info(f"Initialized Azure Speech VAD with sensitivity={self.config.sensitivity}")
    
    def update_ambient_noise(self, noise_level_db: float):
        """
        Update ambient noise level for adaptive threshold.
        
        Args:
            noise_level_db: Current noise level in decibels
        """
        self.noise_samples.append(noise_level_db)
        
        # Keep only recent samples
        if len(self.noise_samples) > self.max_noise_samples:
            self.noise_samples.pop(0)
        
        # Calculate average ambient noise
        self.ambient_noise_level = sum(self.noise_samples) / len(self.noise_samples)
        
        logger.debug(f"Ambient noise level: {self.ambient_noise_level:.2f} dB")
    
    def get_adaptive_threshold(self) -> float:
        """
        Calculate adaptive threshold based on ambient noise.
        
        Returns:
            Adjusted sensitivity threshold
        """
        if not self.config.adaptive_threshold:
            return self.config.sensitivity
        
        # If noise exceeds threshold, increase sensitivity
        if self.ambient_noise_level > self.config.noise_threshold_db:
            # Increase sensitivity by 20% for noisy environments
            adjusted = min(1.0, self.config.sensitivity * 1.2)
            logger.debug(
                f"Adaptive threshold: {adjusted:.2f} "
                f"(noise: {self.ambient_noise_level:.2f} dB)"
            )
            return adjusted
        
        return self.config.sensitivity
    
    def process_audio_level(self, audio_level: float, timestamp: float) -> VADState:
        """
        Process audio level to detect speech activity.
        
        Args:
            audio_level: Audio level (0.0 to 1.0)
            timestamp: Current timestamp in seconds
        
        Returns:
            Current VAD state
        """
        threshold = self.get_adaptive_threshold()
        
        # Detect speech based on audio level
        is_speech = audio_level > threshold
        
        if is_speech:
            if self.current_state == VADState.SILENCE:
                # Transition from silence to speech
                self.speech_start_time = timestamp
                self.silence_start_time = None
                
                # Check minimum speech duration before confirming
                if self.config.boundary_detection:
                    self.current_state = VADState.UNCERTAIN
                else:
                    self.current_state = VADState.SPEECH
                    if self.on_speech_start:
                        self.on_speech_start(timestamp)
                        logger.debug(f"Speech started at {timestamp:.2f}s")
            
            elif self.current_state == VADState.UNCERTAIN:
                # Check if minimum speech duration met
                if self.speech_start_time:
                    duration_ms = (timestamp - self.speech_start_time) * 1000
                    if duration_ms >= self.config.min_speech_duration_ms:
                        self.current_state = VADState.SPEECH
                        if self.on_speech_start:
                            self.on_speech_start(self.speech_start_time)
                            logger.debug(
                                f"Speech confirmed at {self.speech_start_time:.2f}s "
                                f"(duration: {duration_ms:.0f}ms)"
                            )
            
            elif self.current_state == VADState.SPEECH:
                # Continue speech
                self.silence_start_time = None
        
        else:  # Silence detected
            if self.current_state == VADState.SPEECH:
                # Potential end of speech
                if not self.silence_start_time:
                    self.silence_start_time = timestamp
                else:
                    # Check if minimum silence duration met
                    silence_duration_ms = (timestamp - self.silence_start_time) * 1000
                    if silence_duration_ms >= self.config.min_silence_duration_ms:
                        # Confirm end of speech
                        self.current_state = VADState.SILENCE
                        if self.on_speech_end:
                            self.on_speech_end(timestamp)
                            logger.debug(
                                f"Speech ended at {timestamp:.2f}s "
                                f"(silence: {silence_duration_ms:.0f}ms)"
                            )
                        self.speech_start_time = None
            
            elif self.current_state == VADState.UNCERTAIN:
                # False alarm, return to silence
                self.current_state = VADState.SILENCE
                self.speech_start_time = None
        
        return self.current_state
    
    def reset(self):
        """Reset VAD state."""
        self.current_state = VADState.SILENCE
        self.speech_start_time = None
        self.silence_start_time = None
        logger.debug("VAD state reset")
    
    def get_state(self) -> VADState:
        """Get current VAD state."""
        return self.current_state
    
    def is_speech_active(self) -> bool:
        """Check if speech is currently active."""
        return self.current_state == VADState.SPEECH
    
    def get_speech_duration(self, current_time: float) -> Optional[float]:
        """
        Get duration of current speech segment.
        
        Args:
            current_time: Current timestamp in seconds
        
        Returns:
            Speech duration in seconds, or None if no active speech
        """
        if self.current_state == VADState.SPEECH and self.speech_start_time:
            return current_time - self.speech_start_time
        return None


def create_azure_vad(
    sensitivity: float = 0.5,
    adaptive: bool = True,
    on_speech_start: Optional[Callable] = None,
    on_speech_end: Optional[Callable] = None,
) -> AzureSpeechVAD:
    """
    Factory function to create Azure Speech VAD instance.
    
    Args:
        sensitivity: VAD sensitivity (0.0 to 1.0)
        adaptive: Enable adaptive threshold for noisy environments
        on_speech_start: Callback when speech starts
        on_speech_end: Callback when speech ends
    
    Returns:
        Configured AzureSpeechVAD instance
    """
    config = VADConfig(
        sensitivity=sensitivity,
        adaptive_threshold=adaptive,
    )
    
    return AzureSpeechVAD(
        config=config,
        on_speech_start=on_speech_start,
        on_speech_end=on_speech_end,
    )
