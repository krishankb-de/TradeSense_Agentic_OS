"""
Voice Session Manager for TradeSense.

Manages voice session lifecycle, tracks metrics (latency, turn count, API costs),
and integrates with the voice pipeline and agent routing system.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9, 2.10**
"""

import logging
import time
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Voice session status."""
    ACTIVE = "active"
    IDLE = "idle"
    ENDED = "ended"
    ERROR = "error"


@dataclass
class VoiceSessionMetrics:
    """
    Metrics tracked during a voice session.
    
    Tracks:
    - Latency (p50, p95, p99)
    - Turn count and turn-taking accuracy
    - API costs (zero for local processing)
    - Session duration
    """
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    
    # Turn tracking
    turn_count: int = 0
    user_turns: int = 0
    agent_turns: int = 0
    interruptions: int = 0
    
    # Latency tracking
    latencies: List[float] = field(default_factory=list)
    avg_latency: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    
    # Speech duration tracking
    total_speech_duration: float = 0.0
    total_silence_duration: float = 0.0
    
    # API cost tracking (should be zero for local processing)
    api_calls: int = 0
    api_cost: float = 0.0
    
    # Error tracking
    errors: int = 0
    error_messages: List[str] = field(default_factory=list)
    
    def add_latency(self, latency: float) -> None:
        """
        Add a latency measurement and update statistics.
        
        Args:
            latency: Latency in milliseconds
        """
        self.latencies.append(latency)
        self.avg_latency = sum(self.latencies) / len(self.latencies)
        
        # Calculate percentiles
        if len(self.latencies) >= 2:
            sorted_latencies = sorted(self.latencies)
            n = len(sorted_latencies)
            
            self.p50_latency = sorted_latencies[int(n * 0.50)]
            self.p95_latency = sorted_latencies[int(n * 0.95)]
            self.p99_latency = sorted_latencies[min(int(n * 0.99), n - 1)]
    
    def add_error(self, error_message: str) -> None:
        """
        Record an error.
        
        Args:
            error_message: Error description
        """
        self.errors += 1
        self.error_messages.append(error_message)
    
    def get_session_duration(self) -> float:
        """
        Get total session duration in seconds.
        
        Returns:
            Duration in seconds
        """
        end = self.end_time or time.time()
        return end - self.start_time
    
    def get_turn_taking_accuracy(self) -> float:
        """
        Calculate turn-taking accuracy.
        
        Target: 95%+ accuracy (interruptions / total_turns < 5%)
        
        **Validates: Requirement 2.10**
        
        Returns:
            Accuracy as a float between 0.0 and 1.0
        """
        total_turns = self.user_turns + self.agent_turns
        if total_turns == 0:
            return 1.0
        
        # Accuracy = 1 - (interruptions / total_turns)
        accuracy = 1.0 - (self.interruptions / total_turns)
        return max(0.0, min(1.0, accuracy))
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metrics to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "session_id": self.session_id,
            "duration": self.get_session_duration(),
            "turn_count": self.turn_count,
            "user_turns": self.user_turns,
            "agent_turns": self.agent_turns,
            "interruptions": self.interruptions,
            "turn_taking_accuracy": self.get_turn_taking_accuracy(),
            "latency": {
                "avg": self.avg_latency,
                "p50": self.p50_latency,
                "p95": self.p95_latency,
                "p99": self.p99_latency,
            },
            "speech_duration": self.total_speech_duration,
            "silence_duration": self.total_silence_duration,
            "api_calls": self.api_calls,
            "api_cost": self.api_cost,
            "errors": self.errors,
        }


@dataclass
class VoiceSessionModel:
    """
    Voice session model.
    
    Represents an active voice interaction session with:
    - Session lifecycle management
    - Metrics tracking
    - Context management
    - Integration with voice pipeline and agent routing
    """
    session_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    
    # User context
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    customer_id: Optional[str] = None
    technician_id: Optional[str] = None
    job_id: Optional[str] = None
    
    # Session context
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Metrics
    metrics: VoiceSessionMetrics = None
    
    # Voice pipeline session ID (from voice.pipeline.VoiceSession)
    pipeline_session_id: Optional[str] = None
    
    # Current state
    current_intent: Optional[str] = None
    current_agent: Optional[str] = None
    
    # Conversation history
    conversation_turns: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize metrics if not provided."""
        if self.metrics is None:
            self.metrics = VoiceSessionMetrics(
                session_id=self.session_id,
                start_time=time.time()
            )
    
    def add_turn(
        self,
        speaker: str,
        message: str,
        intent: Optional[str] = None,
        agent: Optional[str] = None,
        latency: Optional[float] = None,
    ) -> None:
        """
        Add a conversation turn.
        
        Args:
            speaker: 'user' or 'agent'
            message: Turn message
            intent: Classified intent (optional)
            agent: Agent that handled the turn (optional)
            latency: Processing latency in ms (optional)
        """
        turn = {
            "speaker": speaker,
            "message": message,
            "intent": intent,
            "agent": agent,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.conversation_turns.append(turn)
        self.metrics.turn_count += 1
        
        if speaker == "user":
            self.metrics.user_turns += 1
        elif speaker == "agent":
            self.metrics.agent_turns += 1
        
        if latency is not None:
            self.metrics.add_latency(latency)
        
        if intent:
            self.current_intent = intent
        if agent:
            self.current_agent = agent
        
        self.updated_at = datetime.utcnow()
    
    def add_interruption(self) -> None:
        """Record an interruption."""
        self.metrics.interruptions += 1
        self.updated_at = datetime.utcnow()
    
    def add_error(self, error_message: str) -> None:
        """
        Record an error.
        
        Args:
            error_message: Error description
        """
        self.metrics.add_error(error_message)
        self.updated_at = datetime.utcnow()
    
    def end_session(self) -> None:
        """End the session and finalize metrics."""
        self.status = SessionStatus.ENDED
        self.metrics.end_time = time.time()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert session to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "user_id": self.user_id,
            "user_role": self.user_role,
            "customer_id": self.customer_id,
            "technician_id": self.technician_id,
            "job_id": self.job_id,
            "context": self.context,
            "metrics": self.metrics.to_dict(),
            "pipeline_session_id": self.pipeline_session_id,
            "current_intent": self.current_intent,
            "current_agent": self.current_agent,
            "turn_count": len(self.conversation_turns),
        }


class VoiceSessionManager:
    """
    Voice session manager.
    
    Manages voice session lifecycle:
    - Create and track sessions
    - Update session metrics
    - Integrate with voice pipeline
    - Integrate with agent routing
    - Persist session data
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9, 2.10**
    """
    
    def __init__(
        self,
        voice_pipeline: Optional[Any] = None,
        agent_router: Optional[Any] = None,
        db_session: Optional[Any] = None,
    ):
        """
        Initialize voice session manager.
        
        Args:
            voice_pipeline: Voice pipeline instance (optional)
            agent_router: Agent router instance (optional)
            db_session: Database session for persistence (optional)
        """
        self.voice_pipeline = voice_pipeline
        self.agent_router = agent_router
        self.db_session = db_session
        
        # Active sessions (in-memory)
        self.sessions: Dict[str, VoiceSessionModel] = {}
        
        # Statistics
        self.total_sessions = 0
        self.active_sessions = 0
        
        logger.info("Voice session manager initialized")
    
    def create_session(
        self,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        customer_id: Optional[str] = None,
        technician_id: Optional[str] = None,
        job_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> VoiceSessionModel:
        """
        Create a new voice session.
        
        Args:
            user_id: User ID
            user_role: User role (technician, customer, dispatcher)
            customer_id: Customer ID (optional)
            technician_id: Technician ID (optional)
            job_id: Job ID (optional)
            context: Additional context (optional)
            
        Returns:
            VoiceSessionModel instance
        """
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        session = VoiceSessionModel(
            session_id=session_id,
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            user_id=user_id,
            user_role=user_role,
            customer_id=customer_id,
            technician_id=technician_id,
            job_id=job_id,
            context=context or {},
        )
        
        self.sessions[session_id] = session
        self.total_sessions += 1
        self.active_sessions += 1
        
        logger.info(
            f"Created voice session: {session_id} "
            f"(user_id={user_id}, role={user_role})"
        )
        
        return session
    
    def get_session(self, session_id: str) -> Optional[VoiceSessionModel]:
        """
        Get a session by ID.
        
        Args:
            session_id: Session ID
            
        Returns:
            VoiceSessionModel if found, None otherwise
        """
        return self.sessions.get(session_id)
    
    def update_session(
        self,
        session_id: str,
        **kwargs
    ) -> Optional[VoiceSessionModel]:
        """
        Update session attributes.
        
        Args:
            session_id: Session ID
            **kwargs: Attributes to update
            
        Returns:
            Updated VoiceSessionModel if found, None otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for update")
            return None
        
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        
        session.updated_at = datetime.utcnow()
        
        return session
    
    def end_session(self, session_id: str) -> Optional[VoiceSessionModel]:
        """
        End a voice session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Ended VoiceSessionModel if found, None otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for ending")
            return None
        
        session.end_session()
        self.active_sessions -= 1
        
        # Log final metrics
        metrics = session.metrics
        logger.info(
            f"Ended voice session: {session_id}, "
            f"duration={metrics.get_session_duration():.2f}s, "
            f"turns={metrics.turn_count}, "
            f"interruptions={metrics.interruptions}, "
            f"turn_taking_accuracy={metrics.get_turn_taking_accuracy():.2%}, "
            f"avg_latency={metrics.avg_latency:.2f}ms, "
            f"p95_latency={metrics.p95_latency:.2f}ms, "
            f"api_cost=${metrics.api_cost:.4f}"
        )
        
        # Persist to database if available
        if self.db_session:
            self._persist_session(session)
        
        return session
    
    def add_turn(
        self,
        session_id: str,
        speaker: str,
        message: str,
        intent: Optional[str] = None,
        agent: Optional[str] = None,
        latency: Optional[float] = None,
    ) -> bool:
        """
        Add a conversation turn to a session.
        
        Args:
            session_id: Session ID
            speaker: 'user' or 'agent'
            message: Turn message
            intent: Classified intent (optional)
            agent: Agent that handled the turn (optional)
            latency: Processing latency in ms (optional)
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for adding turn")
            return False
        
        session.add_turn(
            speaker=speaker,
            message=message,
            intent=intent,
            agent=agent,
            latency=latency,
        )
        
        return True
    
    def add_interruption(self, session_id: str) -> bool:
        """
        Record an interruption in a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for adding interruption")
            return False
        
        session.add_interruption()
        return True
    
    def add_error(self, session_id: str, error_message: str) -> bool:
        """
        Record an error in a session.
        
        Args:
            session_id: Session ID
            error_message: Error description
            
        Returns:
            True if successful, False otherwise
        """
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for adding error")
            return False
        
        session.add_error(error_message)
        return True
    
    def get_active_sessions(self) -> List[VoiceSessionModel]:
        """
        Get all active sessions.
        
        Returns:
            List of active VoiceSessionModel instances
        """
        return [
            session for session in self.sessions.values()
            if session.status == SessionStatus.ACTIVE
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get session manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        active_sessions = self.get_active_sessions()
        
        # Calculate aggregate metrics
        total_turns = sum(s.metrics.turn_count for s in active_sessions)
        total_latencies = []
        for session in active_sessions:
            total_latencies.extend(session.metrics.latencies)
        
        avg_latency = sum(total_latencies) / len(total_latencies) if total_latencies else 0.0
        
        return {
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "total_turns": total_turns,
            "avg_latency": avg_latency,
            "sessions": [s.session_id for s in active_sessions],
        }
    
    def cleanup_inactive_sessions(self, timeout_seconds: int = 300) -> int:
        """
        Clean up inactive sessions.
        
        Args:
            timeout_seconds: Inactivity timeout (default: 5 minutes)
            
        Returns:
            Number of sessions cleaned up
        """
        now = datetime.utcnow()
        inactive_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.status != SessionStatus.ACTIVE:
                continue
            
            inactive_duration = (now - session.updated_at).total_seconds()
            if inactive_duration > timeout_seconds:
                inactive_sessions.append(session_id)
        
        for session_id in inactive_sessions:
            logger.info(f"Cleaning up inactive session: {session_id}")
            self.end_session(session_id)
        
        if inactive_sessions:
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")
        
        return len(inactive_sessions)
    
    def _persist_session(self, session: VoiceSessionModel) -> None:
        """
        Persist session to database.
        
        Args:
            session: Session to persist
        """
        if not self.db_session:
            return
        
        try:
            # TODO: Implement database persistence
            # This would save the session to the conversations table
            # and conversation_turns table
            logger.debug(f"Persisting session {session.session_id} to database")
        except Exception as e:
            logger.error(f"Failed to persist session {session.session_id}: {e}")


# Factory function
def create_voice_session_manager(
    voice_pipeline: Optional[Any] = None,
    agent_router: Optional[Any] = None,
    db_session: Optional[Any] = None,
) -> VoiceSessionManager:
    """
    Create a voice session manager.
    
    Args:
        voice_pipeline: Voice pipeline instance (optional)
        agent_router: Agent router instance (optional)
        db_session: Database session for persistence (optional)
        
    Returns:
        VoiceSessionManager instance
    """
    return VoiceSessionManager(
        voice_pipeline=voice_pipeline,
        agent_router=agent_router,
        db_session=db_session,
    )
