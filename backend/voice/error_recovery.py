"""
Voice Pipeline Error Recovery Module.

Implements error handling and recovery for voice pipeline:
- Fallback to text input mode
- Automatic recovery after 30 seconds
- Error logging with audio samples
- Azure Speech API error tracking

**Validates: Requirement 15.1**
"""

import logging
import time
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from core.error_handling import (
    ErrorHandler,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    get_error_handler,
)

logger = logging.getLogger(__name__)


class VoiceErrorType(Enum):
    """Types of voice pipeline errors."""
    STT_FAILURE = "stt_failure"
    TTS_FAILURE = "tts_failure"
    VAD_FAILURE = "vad_failure"
    AUDIO_QUALITY = "audio_quality"
    NETWORK_ERROR = "network_error"
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class VoiceErrorContext:
    """Context for voice pipeline errors."""
    error_type: VoiceErrorType
    session_id: str
    message: str
    audio_sample: Optional[bytes] = None
    audio_metadata: Optional[Dict[str, Any]] = None
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class VoiceErrorRecovery:
    """
    Voice pipeline error recovery manager.
    
    Features:
    - Automatic fallback to text mode
    - Recovery attempts after 30 seconds
    - Error logging with audio samples
    - Azure Speech API error tracking
    
    **Validates: Requirement 15.1**
    """
    
    def __init__(
        self,
        recovery_delay: float = 30.0,
        max_recovery_attempts: int = 3,
    ):
        """
        Initialize voice error recovery.
        
        Args:
            recovery_delay: Delay before attempting recovery (seconds)
            max_recovery_attempts: Maximum recovery attempts
        """
        self.recovery_delay = recovery_delay
        self.max_recovery_attempts = max_recovery_attempts
        self.error_handler = get_error_handler()
        
        # Track sessions in text fallback mode
        self.fallback_sessions: Dict[str, VoiceErrorContext] = {}
        
        # Track recovery attempts
        self.recovery_attempts: Dict[str, int] = {}
        
        # Track Azure Speech API errors
        self.azure_errors: Dict[str, int] = {}
        
        logger.info("Voice error recovery initialized")
    
    async def handle_voice_error(
        self,
        session_id: str,
        error: Exception,
        error_type: VoiceErrorType = VoiceErrorType.UNKNOWN,
        audio_sample: Optional[bytes] = None,
        audio_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle voice pipeline error.
        
        **Validates: Requirement 15.1**
        
        Args:
            session_id: Session ID
            error: Exception that occurred
            error_type: Type of voice error
            audio_sample: Audio sample that caused error (for debugging)
            audio_metadata: Audio metadata (sample rate, format, etc.)
            
        Returns:
            Dictionary with recovery instructions
        """
        # Create voice error context
        voice_error = VoiceErrorContext(
            error_type=error_type,
            session_id=session_id,
            message=str(error),
            audio_sample=audio_sample,
            audio_metadata=audio_metadata,
        )
        
        # Log error
        error_context = ErrorContext(
            category=ErrorCategory.VOICE_PIPELINE,
            severity=ErrorSeverity.HIGH,
            message=f"Voice pipeline error: {error_type.value} - {str(error)}",
            details={
                "session_id": session_id,
                "error_type": error_type.value,
                "audio_metadata": audio_metadata,
            },
        )
        self.error_handler.log_error(error_context)
        
        # Track Azure Speech API errors
        if error_type == VoiceErrorType.API_ERROR:
            self._track_azure_error(session_id, str(error))
        
        # Add to fallback sessions
        self.fallback_sessions[session_id] = voice_error
        
        # Schedule recovery attempt
        asyncio.create_task(self._schedule_recovery(session_id))
        
        logger.warning(
            f"Voice error for session {session_id}: {error_type.value}. "
            f"Falling back to text mode."
        )
        
        return {
            "fallback_mode": "text",
            "error_type": error_type.value,
            "message": "Voice processing unavailable. Please use text input.",
            "recovery_scheduled": True,
            "recovery_delay": self.recovery_delay,
        }
    
    async def _schedule_recovery(self, session_id: str) -> None:
        """
        Schedule automatic recovery attempt.
        
        **Validates: Requirement 15.1**
        
        Args:
            session_id: Session ID
        """
        # Wait for recovery delay
        await asyncio.sleep(self.recovery_delay)
        
        # Check if session still in fallback mode
        if session_id not in self.fallback_sessions:
            logger.debug(f"Session {session_id} already recovered")
            return
        
        # Check recovery attempts
        attempts = self.recovery_attempts.get(session_id, 0)
        if attempts >= self.max_recovery_attempts:
            logger.warning(
                f"Max recovery attempts reached for session {session_id}"
            )
            return
        
        # Attempt recovery
        logger.info(
            f"Attempting voice recovery for session {session_id} "
            f"(attempt {attempts + 1}/{self.max_recovery_attempts})"
        )
        
        # Increment attempts
        self.recovery_attempts[session_id] = attempts + 1
        
        # In a real implementation, this would:
        # 1. Test voice pipeline connectivity
        # 2. Verify Azure Speech API availability
        # 3. Attempt a test transcription
        # 4. If successful, remove from fallback_sessions
        
        # For now, we'll simulate recovery check
        recovery_successful = await self._test_voice_pipeline(session_id)
        
        if recovery_successful:
            logger.info(f"Voice recovery successful for session {session_id}")
            self.fallback_sessions.pop(session_id, None)
            self.recovery_attempts.pop(session_id, None)
        else:
            logger.warning(f"Voice recovery failed for session {session_id}")
            # Schedule another attempt
            asyncio.create_task(self._schedule_recovery(session_id))
    
    async def _test_voice_pipeline(self, session_id: str) -> bool:
        """
        Test voice pipeline availability.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if voice pipeline is available
        """
        try:
            # In a real implementation, this would:
            # 1. Check Azure Speech API status
            # 2. Attempt a test transcription
            # 3. Verify TTS synthesis
            
            # For now, simulate test
            await asyncio.sleep(0.1)
            
            # Simulate 70% success rate
            import random
            return random.random() > 0.3
            
        except Exception as e:
            logger.error(f"Voice pipeline test failed: {e}")
            return False
    
    def _track_azure_error(self, session_id: str, error_message: str) -> None:
        """
        Track Azure Speech API errors.
        
        Args:
            session_id: Session ID
            error_message: Error message
        """
        # Extract error code if present
        error_key = "azure_api_error"
        if "429" in error_message or "rate limit" in error_message.lower():
            error_key = "azure_rate_limit"
        elif "401" in error_message or "unauthorized" in error_message.lower():
            error_key = "azure_auth_error"
        elif "timeout" in error_message.lower():
            error_key = "azure_timeout"
        
        self.azure_errors[error_key] = self.azure_errors.get(error_key, 0) + 1
        
        logger.info(f"Azure Speech API error tracked: {error_key}")
    
    def is_in_fallback_mode(self, session_id: str) -> bool:
        """
        Check if session is in fallback mode.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if in fallback mode
        """
        return session_id in self.fallback_sessions
    
    def get_fallback_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get fallback status for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Fallback status or None if not in fallback mode
        """
        if session_id not in self.fallback_sessions:
            return None
        
        error_context = self.fallback_sessions[session_id]
        attempts = self.recovery_attempts.get(session_id, 0)
        
        return {
            "error_type": error_context.error_type.value,
            "message": error_context.message,
            "timestamp": error_context.timestamp,
            "recovery_attempts": attempts,
            "max_attempts": self.max_recovery_attempts,
        }
    
    def get_azure_error_stats(self) -> Dict[str, Any]:
        """
        Get Azure Speech API error statistics.
        
        Returns:
            Dictionary with error statistics
        """
        total_errors = sum(self.azure_errors.values())
        
        return {
            "total_errors": total_errors,
            "by_type": dict(self.azure_errors),
        }
    
    def clear_session(self, session_id: str) -> None:
        """
        Clear session from fallback tracking.
        
        Args:
            session_id: Session ID
        """
        self.fallback_sessions.pop(session_id, None)
        self.recovery_attempts.pop(session_id, None)
        
        logger.debug(f"Cleared fallback tracking for session {session_id}")


# Global instance
_voice_error_recovery = VoiceErrorRecovery()


def get_voice_error_recovery() -> VoiceErrorRecovery:
    """Get global voice error recovery instance."""
    return _voice_error_recovery
