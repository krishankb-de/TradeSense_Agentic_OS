"""
Streaming Response Handler for Voice-to-Agent Integration.

Implements:
- Streaming partial transcriptions for responsiveness
- Interruption handling during streaming
- Turn-taking detection
- Real-time agent response streaming

**Validates: Requirements 2.8, 2.9, 2.10**
"""

import logging
import time
import asyncio
from typing import Optional, Dict, Any, Callable, AsyncIterator
from dataclasses import dataclass
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class StreamEventType(str, Enum):
    """Types of streaming events."""
    PARTIAL_TRANSCRIPTION = "partial_transcription"
    FINAL_TRANSCRIPTION = "final_transcription"
    AGENT_RESPONSE_START = "agent_response_start"
    AGENT_RESPONSE_CHUNK = "agent_response_chunk"
    AGENT_RESPONSE_END = "agent_response_end"
    SPEECH_START = "speech_start"
    SPEECH_END = "speech_end"
    SILENCE_DETECTED = "silence_detected"
    INTERRUPTION = "interruption"
    ERROR = "error"


@dataclass
class StreamEvent:
    """Streaming event."""
    event_type: StreamEventType
    data: Any
    timestamp: float
    session_id: str
    metadata: Optional[Dict[str, Any]] = None


class TurnTakingDetector:
    """
    Turn-taking detector for voice interactions.
    
    Detects when:
    - User has finished speaking (silence after speech)
    - Agent should start speaking
    - User is interrupting agent
    
    **Validates: Requirement 2.10**
    """
    
    def __init__(
        self,
        silence_threshold_ms: int = 500,
        min_speech_duration_ms: int = 100,
    ):
        """
        Initialize turn-taking detector.
        
        Args:
            silence_threshold_ms: Silence duration to detect turn end
            min_speech_duration_ms: Minimum speech duration to consider valid
        """
        self.silence_threshold_ms = silence_threshold_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        
        # State tracking
        self.is_user_speaking = False
        self.is_agent_speaking = False
        self.last_speech_time: Optional[float] = None
        self.speech_start_time: Optional[float] = None
        
        logger.info(
            f"Turn-taking detector initialized: "
            f"silence_threshold={silence_threshold_ms}ms, "
            f"min_speech={min_speech_duration_ms}ms"
        )
    
    def on_speech_start(self) -> bool:
        """
        Handle speech start event.
        
        Returns:
            True if this is an interruption, False otherwise
        """
        now = time.time()
        self.speech_start_time = now
        self.last_speech_time = now
        
        # Check if agent is speaking (interruption)
        is_interruption = self.is_agent_speaking
        
        self.is_user_speaking = True
        
        if is_interruption:
            logger.info("Interruption detected: user started speaking while agent was speaking")
        
        return is_interruption
    
    def on_speech_end(self) -> bool:
        """
        Handle speech end event.
        
        Returns:
            True if turn is complete, False otherwise
        """
        now = time.time()
        self.last_speech_time = now
        
        # Check if speech was long enough
        if self.speech_start_time:
            speech_duration = (now - self.speech_start_time) * 1000  # Convert to ms
            if speech_duration < self.min_speech_duration_ms:
                logger.debug(f"Speech too short: {speech_duration:.2f}ms")
                return False
        
        self.is_user_speaking = False
        
        return True
    
    def on_silence(self, duration_ms: float) -> bool:
        """
        Handle silence detection.
        
        Args:
            duration_ms: Silence duration in milliseconds
            
        Returns:
            True if turn should end, False otherwise
        """
        if duration_ms >= self.silence_threshold_ms:
            logger.debug(f"Turn-ending silence detected: {duration_ms:.2f}ms")
            return True
        
        return False
    
    def on_agent_start(self) -> None:
        """Handle agent speech start."""
        self.is_agent_speaking = True
        self.is_user_speaking = False
    
    def on_agent_end(self) -> None:
        """Handle agent speech end."""
        self.is_agent_speaking = False
    
    def get_turn_state(self) -> str:
        """
        Get current turn state.
        
        Returns:
            'user_turn', 'agent_turn', or 'transition'
        """
        if self.is_user_speaking:
            return "user_turn"
        elif self.is_agent_speaking:
            return "agent_turn"
        else:
            return "transition"


class StreamingResponseHandler:
    """
    Streaming response handler for voice-to-agent integration.
    
    Features:
    - Stream partial transcriptions for responsiveness
    - Detect and handle interruptions
    - Manage turn-taking
    - Buffer and stream agent responses
    
    **Validates: Requirements 2.8, 2.9, 2.10**
    """
    
    def __init__(
        self,
        session_id: str,
        turn_detector: Optional[TurnTakingDetector] = None,
    ):
        """
        Initialize streaming response handler.
        
        Args:
            session_id: Session ID
            turn_detector: Turn-taking detector (optional)
        """
        self.session_id = session_id
        self.turn_detector = turn_detector or TurnTakingDetector()
        
        # Event queue
        self.event_queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        
        # Callbacks
        self.on_interruption: Optional[Callable] = None
        self.on_turn_complete: Optional[Callable] = None
        
        # State
        self.is_streaming = False
        self.current_transcription = ""
        self.partial_transcription = ""
        
        # Metrics
        self.events_processed = 0
        self.interruptions_detected = 0
        
        logger.info(f"Streaming response handler initialized for session {session_id}")
    
    async def start_streaming(self) -> None:
        """Start streaming mode."""
        self.is_streaming = True
        logger.info(f"Started streaming for session {self.session_id}")
    
    async def stop_streaming(self) -> None:
        """Stop streaming mode."""
        self.is_streaming = False
        logger.info(
            f"Stopped streaming for session {self.session_id}: "
            f"events_processed={self.events_processed}, "
            f"interruptions={self.interruptions_detected}"
        )
    
    async def handle_partial_transcription(
        self,
        text: str,
        confidence: float = 0.8,
    ) -> StreamEvent:
        """
        Handle partial transcription event.
        
        **Validates: Requirement 2.8**
        
        Args:
            text: Partial transcription text
            confidence: Confidence score
            
        Returns:
            StreamEvent
        """
        self.partial_transcription = text
        
        event = StreamEvent(
            event_type=StreamEventType.PARTIAL_TRANSCRIPTION,
            data={
                "text": text,
                "confidence": confidence,
                "is_final": False,
            },
            timestamp=time.time(),
            session_id=self.session_id,
        )
        
        await self.event_queue.put(event)
        self.events_processed += 1
        
        logger.debug(f"Partial transcription: {text[:50]}...")
        
        return event
    
    async def handle_final_transcription(
        self,
        text: str,
        confidence: float = 1.0,
    ) -> StreamEvent:
        """
        Handle final transcription event.
        
        Args:
            text: Final transcription text
            confidence: Confidence score
            
        Returns:
            StreamEvent
        """
        self.current_transcription = text
        self.partial_transcription = ""
        
        event = StreamEvent(
            event_type=StreamEventType.FINAL_TRANSCRIPTION,
            data={
                "text": text,
                "confidence": confidence,
                "is_final": True,
            },
            timestamp=time.time(),
            session_id=self.session_id,
        )
        
        await self.event_queue.put(event)
        self.events_processed += 1
        
        logger.info(f"Final transcription: {text}")
        
        return event
    
    async def handle_speech_start(self) -> StreamEvent:
        """
        Handle speech start event.
        
        **Validates: Requirement 2.9**
        
        Returns:
            StreamEvent
        """
        is_interruption = self.turn_detector.on_speech_start()
        
        event_type = StreamEventType.INTERRUPTION if is_interruption else StreamEventType.SPEECH_START
        
        event = StreamEvent(
            event_type=event_type,
            data={
                "is_interruption": is_interruption,
                "turn_state": self.turn_detector.get_turn_state(),
            },
            timestamp=time.time(),
            session_id=self.session_id,
        )
        
        await self.event_queue.put(event)
        self.events_processed += 1
        
        if is_interruption:
            self.interruptions_detected += 1
            if self.on_interruption:
                self.on_interruption(self.session_id)
        
        return event
    
    async def handle_speech_end(self) -> StreamEvent:
        """
        Handle speech end event.
        
        **Validates: Requirement 2.10**
        
        Returns:
            StreamEvent
        """
        turn_complete = self.turn_detector.on_speech_end()
        
        event = StreamEvent(
            event_type=StreamEventType.SPEECH_END,
            data={
                "turn_complete": turn_complete,
                "turn_state": self.turn_detector.get_turn_state(),
            },
            timestamp=time.time(),
            session_id=self.session_id,
        )
        
        await self.event_queue.put(event)
        self.events_processed += 1
        
        if turn_complete and self.on_turn_complete:
            self.on_turn_complete(self.session_id)
        
        return event
    
    async def handle_silence(self, duration_ms: float) -> Optional[StreamEvent]:
        """
        Handle silence detection.
        
        Args:
            duration_ms: Silence duration in milliseconds
            
        Returns:
            StreamEvent if turn should end, None otherwise
        """
        should_end_turn = self.turn_detector.on_silence(duration_ms)
        
        if should_end_turn:
            event = StreamEvent(
                event_type=StreamEventType.SILENCE_DETECTED,
                data={
                    "duration_ms": duration_ms,
                    "turn_complete": True,
                },
                timestamp=time.time(),
                session_id=self.session_id,
            )
            
            await self.event_queue.put(event)
            self.events_processed += 1
            
            if self.on_turn_complete:
                self.on_turn_complete(self.session_id)
            
            return event
        
        return None
    
    async def handle_agent_response_start(self) -> StreamEvent:
        """
        Handle agent response start.
        
        Returns:
            StreamEvent
        """
        self.turn_detector.on_agent_start()
        
        event = StreamEvent(
            event_type=StreamEventType.AGENT_RESPONSE_START,
            data={
                "turn_state": self.turn_detector.get_turn_state(),
            },
            timestamp=time.time(),
            session_id=self.session_id,
        )
        
        await self.event_queue.put(event)
        self.events_processed += 1
        
        return event
    
    async def handle_agent_response_chunk(
        self,
        text: str,
        audio_chunk: Optional[bytes] = None,
    ) -> StreamEvent:
        """
        Handle agent response chunk.
        
        Args:
            text: Response text chunk
            audio_chunk: Audio data chunk (optional)
            
        Returns:
            StreamEvent
        """
        event = StreamEvent(
            event_type=StreamEventType.AGENT_RESPONSE_CHUNK,
            data={
                "text": text,
                "has_audio": audio_chunk is not None,
                "audio_size": len(audio_chunk) if audio_chunk else 0,
            },
            timestamp=time.time(),
            session_id=self.session_id,
            metadata={
                "audio_chunk": audio_chunk,
            },
        )
        
        await self.event_queue.put(event)
        self.events_processed += 1
        
        return event
    
    async def handle_agent_response_end(self) -> StreamEvent:
        """
        Handle agent response end.
        
        Returns:
            StreamEvent
        """
        self.turn_detector.on_agent_end()
        
        event = StreamEvent(
            event_type=StreamEventType.AGENT_RESPONSE_END,
            data={
                "turn_state": self.turn_detector.get_turn_state(),
            },
            timestamp=time.time(),
            session_id=self.session_id,
        )
        
        await self.event_queue.put(event)
        self.events_processed += 1
        
        return event
    
    async def handle_error(self, error: str) -> StreamEvent:
        """
        Handle error event.
        
        Args:
            error: Error message
            
        Returns:
            StreamEvent
        """
        event = StreamEvent(
            event_type=StreamEventType.ERROR,
            data={
                "error": error,
            },
            timestamp=time.time(),
            session_id=self.session_id,
        )
        
        await self.event_queue.put(event)
        self.events_processed += 1
        
        logger.error(f"Streaming error for session {self.session_id}: {error}")
        
        return event
    
    async def get_events(self) -> AsyncIterator[StreamEvent]:
        """
        Get streaming events as they occur.
        
        Yields:
            StreamEvent instances
        """
        while self.is_streaming or not self.event_queue.empty():
            try:
                # Wait for event with timeout
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=0.1
                )
                yield event
            except asyncio.TimeoutError:
                # No event available, continue
                continue
            except Exception as e:
                logger.error(f"Error getting event: {e}")
                break
    
    def set_callbacks(
        self,
        on_interruption: Optional[Callable] = None,
        on_turn_complete: Optional[Callable] = None,
    ) -> None:
        """
        Set callbacks for streaming events.
        
        Args:
            on_interruption: Called when interruption is detected
            on_turn_complete: Called when turn is complete
        """
        self.on_interruption = on_interruption
        self.on_turn_complete = on_turn_complete
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get streaming metrics.
        
        Returns:
            Dictionary with metrics
        """
        return {
            "session_id": self.session_id,
            "events_processed": self.events_processed,
            "interruptions_detected": self.interruptions_detected,
            "is_streaming": self.is_streaming,
            "turn_state": self.turn_detector.get_turn_state(),
        }


# Factory function
def create_streaming_handler(
    session_id: str,
    silence_threshold_ms: int = 500,
    min_speech_duration_ms: int = 100,
) -> StreamingResponseHandler:
    """
    Create a streaming response handler.
    
    Args:
        session_id: Session ID
        silence_threshold_ms: Silence duration to detect turn end
        min_speech_duration_ms: Minimum speech duration to consider valid
        
    Returns:
        StreamingResponseHandler instance
    """
    turn_detector = TurnTakingDetector(
        silence_threshold_ms=silence_threshold_ms,
        min_speech_duration_ms=min_speech_duration_ms,
    )
    
    return StreamingResponseHandler(
        session_id=session_id,
        turn_detector=turn_detector,
    )
