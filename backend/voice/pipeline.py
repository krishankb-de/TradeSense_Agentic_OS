"""
Voice Pipeline Orchestrator
Coordinates Azure Speech STT, TTS, and VAD for real-time voice interactions
Implements session management, turn-taking, and interruption handling
"""

import logging
import time
import uuid
from typing import Optional, Dict, Callable, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from voice.stt import AzureSpeechSTT, TranscriptionChunk, create_azure_stt
from voice.tts import AzureSpeechTTS, VoiceConfig, VoiceStyle, create_azure_tts
from voice.vad import AzureSpeechVAD, VADConfig, VADState, create_azure_vad

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    """Voice session states."""
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"
    ENDED = "ended"


class TurnState(str, Enum):
    """Turn-taking states."""
    USER_TURN = "user_turn"
    AGENT_TURN = "agent_turn"
    TRANSITION = "transition"


@dataclass
class SessionMetrics:
    """Metrics tracked during a voice session."""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    turn_count: int = 0
    user_turns: int = 0
    agent_turns: int = 0
    interruptions: int = 0
    total_speech_duration: float = 0.0
    total_silence_duration: float = 0.0
    avg_latency: float = 0.0
    latencies: list = field(default_factory=list)
    
    def add_latency(self, latency: float):
        """Add a latency measurement."""
        self.latencies.append(latency)
        self.avg_latency = sum(self.latencies) / len(self.latencies)
    
    def get_session_duration(self) -> float:
        """Get total session duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time
    
    def get_turn_taking_accuracy(self) -> float:
        """
        Calculate turn-taking accuracy.
        Target: 95%+ accuracy (interruptions / total_turns < 5%)
        """
        total_turns = self.user_turns + self.agent_turns
        if total_turns == 0:
            return 1.0
        
        # Accuracy = 1 - (interruptions / total_turns)
        accuracy = 1.0 - (self.interruptions / total_turns)
        return max(0.0, min(1.0, accuracy))


@dataclass
class VoiceSession:
    """Represents an active voice session."""
    session_id: str
    state: SessionState
    turn_state: TurnState
    context: Dict
    metrics: SessionMetrics
    created_at: datetime
    last_activity: datetime
    
    # Components
    stt: Optional[AzureSpeechSTT] = None
    tts: Optional[AzureSpeechTTS] = None
    vad: Optional[AzureSpeechVAD] = None
    
    # Current transcription
    current_transcription: str = ""
    partial_transcription: str = ""
    
    # Interruption handling
    can_be_interrupted: bool = True
    interrupt_requested: bool = False


@dataclass
class VoicePipelineConfig:
    """Configuration for voice pipeline."""
    # Azure Speech credentials
    azure_speech_key: str
    azure_speech_region: str
    
    # STT configuration
    stt_language: str = "en-US"
    stt_enable_dictation: bool = True
    stt_enable_profanity_filter: bool = True
    
    # TTS configuration
    tts_voice_name: str = "en-US-JennyNeural"
    tts_default_style: VoiceStyle = VoiceStyle.NEUTRAL
    
    # VAD configuration
    vad_sensitivity: float = 0.5
    vad_min_speech_duration_ms: int = 100
    vad_min_silence_duration_ms: int = 500
    vad_adaptive_threshold: bool = True
    
    # Latency targets
    latency_target_ms: int = 500
    tts_latency_target_ms: int = 100
    
    # Session configuration
    max_session_duration_seconds: int = 3600  # 1 hour
    session_timeout_seconds: int = 300  # 5 minutes of inactivity


class VoicePipeline:
    """
    Voice Pipeline Orchestrator.
    
    Coordinates Azure Speech STT, TTS, and VAD for real-time voice interactions.
    Implements session management, turn-taking, and interruption handling.
    
    Features:
    - Session lifecycle management
    - Turn-taking with 95%+ accuracy
    - Interruption handling
    - Latency tracking (<500ms target)
    - State management
    """
    
    def __init__(self, config: VoicePipelineConfig):
        """
        Initialize voice pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        
        # Active sessions
        self.sessions: Dict[str, VoiceSession] = {}
        
        # Callbacks
        self.on_transcription: Optional[Callable] = None
        self.on_speech_start: Optional[Callable] = None
        self.on_speech_end: Optional[Callable] = None
        self.on_interruption: Optional[Callable] = None
        
        logger.info(
            f"Initialized VoicePipeline: "
            f"latency_target={config.latency_target_ms}ms, "
            f"language={config.stt_language}, "
            f"voice={config.tts_voice_name}"
        )
    
    async def initialize(self) -> None:
        """
        Initialize pipeline components.
        
        This method can be used for any async initialization needed.
        """
        logger.info("Voice pipeline initialized and ready")
    
    async def start_session(
        self,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> VoiceSession:
        """
        Start a new voice session.
        
        Args:
            session_id: Optional session ID (generated if not provided)
            context: Optional session context
            
        Returns:
            VoiceSession instance
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Check if session already exists
        if session_id in self.sessions:
            logger.warning(f"Session {session_id} already exists, returning existing session")
            return self.sessions[session_id]
        
        # Create STT client
        stt = create_azure_stt(
            subscription_key=self.config.azure_speech_key,
            region=self.config.azure_speech_region,
            language=self.config.stt_language,
            enable_dictation=self.config.stt_enable_dictation,
            enable_profanity_filter=self.config.stt_enable_profanity_filter,
        )
        
        # Create TTS client
        tts = create_azure_tts(
            subscription_key=self.config.azure_speech_key,
            region=self.config.azure_speech_region,
            voice_name=self.config.tts_voice_name,
        )
        
        # Create VAD instance
        vad = create_azure_vad(
            sensitivity=self.config.vad_sensitivity,
            adaptive=self.config.vad_adaptive_threshold,
            on_speech_start=lambda ts: self._on_vad_speech_start(session_id, ts),
            on_speech_end=lambda ts: self._on_vad_speech_end(session_id, ts),
        )
        
        # Create session
        now = datetime.now()
        session = VoiceSession(
            session_id=session_id,
            state=SessionState.IDLE,
            turn_state=TurnState.USER_TURN,
            context=context or {},
            metrics=SessionMetrics(
                session_id=session_id,
                start_time=time.time()
            ),
            created_at=now,
            last_activity=now,
            stt=stt,
            tts=tts,
            vad=vad,
        )
        
        self.sessions[session_id] = session
        
        logger.info(f"Started voice session: {session_id}")
        return session
    
    async def end_session(self, session_id: str) -> None:
        """
        End a voice session.
        
        Args:
            session_id: Session ID to end
        """
        if session_id not in self.sessions:
            logger.warning(f"Session {session_id} not found")
            return
        
        session = self.sessions[session_id]
        session.state = SessionState.ENDED
        session.metrics.end_time = time.time()
        
        # Log session metrics
        logger.info(
            f"Ended voice session: {session_id}, "
            f"duration={session.metrics.get_session_duration():.2f}s, "
            f"turns={session.metrics.turn_count}, "
            f"interruptions={session.metrics.interruptions}, "
            f"turn_taking_accuracy={session.metrics.get_turn_taking_accuracy():.2%}, "
            f"avg_latency={session.metrics.avg_latency:.2f}ms"
        )
        
        # Remove from active sessions
        del self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[VoiceSession]:
        """
        Get an active session.
        
        Args:
            session_id: Session ID
            
        Returns:
            VoiceSession if found, None otherwise
        """
        return self.sessions.get(session_id)
    
    async def process_audio_stream(
        self,
        session_id: str,
        audio_config,
    ) -> None:
        """
        Process audio stream for a session.
        
        This sets up continuous recognition with callbacks.
        
        Args:
            session_id: Session ID
            audio_config: Azure Speech AudioConfig
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Update session state
        session.state = SessionState.LISTENING
        session.last_activity = datetime.now()
        
        # Define callbacks for streaming recognition
        def on_recognizing(evt):
            """Handle partial transcription."""
            session.partial_transcription = evt.result.text
            session.last_activity = datetime.now()
            
            if self.on_transcription:
                self.on_transcription(session_id, evt.result.text, is_final=False)
        
        def on_recognized(evt):
            """Handle final transcription."""
            if evt.result.text:
                session.current_transcription = evt.result.text
                session.partial_transcription = ""
                session.metrics.user_turns += 1
                session.metrics.turn_count += 1
                session.last_activity = datetime.now()
                
                # Transition to processing
                session.state = SessionState.PROCESSING
                session.turn_state = TurnState.TRANSITION
                
                if self.on_transcription:
                    self.on_transcription(session_id, evt.result.text, is_final=True)
        
        def on_canceled(evt):
            """Handle recognition errors."""
            logger.error(f"Recognition canceled for session {session_id}: {evt.cancellation_details}")
            session.state = SessionState.IDLE
        
        # Start continuous recognition
        recognizer = await session.stt.transcribe_stream(
            audio_config=audio_config,
            callback_recognizing=on_recognizing,
            callback_recognized=on_recognized,
            callback_canceled=on_canceled,
        )
        
        # Store recognizer in session context for later cleanup
        session.context['recognizer'] = recognizer
        
        logger.info(f"Started audio stream processing for session {session_id}")
    
    async def synthesize_speech(
        self,
        session_id: str,
        text: str,
        voice_config: Optional[VoiceConfig] = None,
    ) -> bytes:
        """
        Synthesize speech for a session.
        
        Args:
            session_id: Session ID
            text: Text to synthesize
            voice_config: Optional voice customization
            
        Returns:
            Audio data bytes
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Update session state
        session.state = SessionState.SPEAKING
        session.turn_state = TurnState.AGENT_TURN
        session.last_activity = datetime.now()
        
        start_time = time.time()
        
        # Use default voice config if not provided
        if voice_config is None:
            voice_config = VoiceConfig(
                voice_name=self.config.tts_voice_name,
                style=self.config.tts_default_style,
            )
        
        # Synthesize
        result = await session.tts.synthesize(
            text=text,
            voice_config=voice_config,
            use_ssml=True
        )
        
        if not result.success:
            logger.error(f"TTS synthesis failed for session {session_id}: {result.error_message}")
            session.state = SessionState.IDLE
            raise RuntimeError(f"TTS synthesis failed: {result.error_message}")
        
        # Track metrics
        latency = (time.time() - start_time) * 1000
        session.metrics.add_latency(latency)
        session.metrics.agent_turns += 1
        session.metrics.turn_count += 1
        
        # Check latency target
        if latency > self.config.tts_latency_target_ms:
            logger.warning(
                f"TTS latency ({latency:.2f}ms) exceeded target "
                f"({self.config.tts_latency_target_ms}ms) for session {session_id}"
            )
        
        # Update state
        session.state = SessionState.LISTENING
        session.turn_state = TurnState.USER_TURN
        
        logger.info(
            f"Synthesized speech for session {session_id}: "
            f"text_length={len(text)}, latency={latency:.2f}ms"
        )
        
        return result.audio_data
    
    def handle_interruption(self, session_id: str) -> bool:
        """
        Handle user interruption during agent speech.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if interruption was handled, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for interruption")
            return False
        
        # Check if interruption is allowed
        if not session.can_be_interrupted:
            logger.debug(f"Session {session_id} cannot be interrupted")
            return False
        
        # Check if agent is speaking
        if session.state != SessionState.SPEAKING:
            logger.debug(f"Session {session_id} is not speaking, no interruption needed")
            return False
        
        # Handle interruption
        session.interrupt_requested = True
        session.state = SessionState.INTERRUPTED
        session.turn_state = TurnState.USER_TURN
        session.metrics.interruptions += 1
        
        logger.info(f"Handled interruption for session {session_id}")
        
        # Call interruption callback
        if self.on_interruption:
            self.on_interruption(session_id)
        
        return True
    
    def _on_vad_speech_start(self, session_id: str, timestamp: float):
        """
        Internal callback for VAD speech start.
        
        Args:
            session_id: Session ID
            timestamp: Speech start timestamp
        """
        session = self.get_session(session_id)
        if not session:
            return
        
        logger.debug(f"VAD detected speech start for session {session_id} at {timestamp:.2f}s")
        
        # Check for interruption
        if session.state == SessionState.SPEAKING:
            self.handle_interruption(session_id)
        
        # Call external callback
        if self.on_speech_start:
            self.on_speech_start(session_id, timestamp)
    
    def _on_vad_speech_end(self, session_id: str, timestamp: float):
        """
        Internal callback for VAD speech end.
        
        Args:
            session_id: Session ID
            timestamp: Speech end timestamp
        """
        session = self.get_session(session_id)
        if not session:
            return
        
        logger.debug(f"VAD detected speech end for session {session_id} at {timestamp:.2f}s")
        
        # Call external callback
        if self.on_speech_end:
            self.on_speech_end(session_id, timestamp)
    
    def set_callbacks(
        self,
        on_transcription: Optional[Callable] = None,
        on_speech_start: Optional[Callable] = None,
        on_speech_end: Optional[Callable] = None,
        on_interruption: Optional[Callable] = None,
    ):
        """
        Set pipeline callbacks.
        
        Args:
            on_transcription: Called when transcription is available
            on_speech_start: Called when speech starts
            on_speech_end: Called when speech ends
            on_interruption: Called when interruption occurs
        """
        self.on_transcription = on_transcription
        self.on_speech_start = on_speech_start
        self.on_speech_end = on_speech_end
        self.on_interruption = on_interruption
    
    def get_session_metrics(self, session_id: str) -> Optional[SessionMetrics]:
        """
        Get metrics for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            SessionMetrics if session found, None otherwise
        """
        session = self.get_session(session_id)
        if session:
            return session.metrics
        return None
    
    async def cleanup_inactive_sessions(self, timeout_seconds: Optional[int] = None):
        """
        Clean up inactive sessions.
        
        Args:
            timeout_seconds: Inactivity timeout (uses config default if not provided)
        """
        if timeout_seconds is None:
            timeout_seconds = self.config.session_timeout_seconds
        
        now = datetime.now()
        inactive_sessions = []
        
        for session_id, session in self.sessions.items():
            inactive_duration = (now - session.last_activity).total_seconds()
            if inactive_duration > timeout_seconds:
                inactive_sessions.append(session_id)
        
        for session_id in inactive_sessions:
            logger.info(f"Cleaning up inactive session: {session_id}")
            await self.end_session(session_id)
        
        if inactive_sessions:
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")


# Factory function
def create_voice_pipeline(
    azure_speech_key: str,
    azure_speech_region: str,
    **kwargs
) -> VoicePipeline:
    """
    Factory function to create voice pipeline.
    
    Args:
        azure_speech_key: Azure Speech Services API key
        azure_speech_region: Azure region
        **kwargs: Additional configuration options
        
    Returns:
        Configured VoicePipeline instance
    """
    config = VoicePipelineConfig(
        azure_speech_key=azure_speech_key,
        azure_speech_region=azure_speech_region,
        **kwargs
    )
    
    return VoicePipeline(config)
