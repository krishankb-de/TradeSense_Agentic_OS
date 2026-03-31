"""
Conversation Context Manager for TradeSense Multi-Agent System.

This module provides session state management and conversation context tracking
using Redis for distributed state storage.

**Validates: Requirements 3.2, 4.10**
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# Context Models
# ============================================================================


class UserRole(str, Enum):
    """User role types."""
    TECHNICIAN = "technician"
    CUSTOMER = "customer"
    DISPATCHER = "dispatcher"
    ADMIN = "admin"


class SessionState(str, Enum):
    """Session state types."""
    ACTIVE = "active"
    WAITING = "waiting"
    COMPLETED = "completed"
    EXPIRED = "expired"


@dataclass
class ConversationTurn:
    """Single conversation turn."""
    turn_id: str
    speaker: str  # 'user' or 'agent'
    content: str
    timestamp: datetime
    agent_type: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    actions: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationTurn':
        """Create from dictionary."""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class ConversationContext:
    """
    Conversation context with session state and history.
    
    **Validates: Requirements 3.2, 4.10**
    """
    session_id: str
    user_id: str
    user_role: UserRole
    state: SessionState
    current_intent: Optional[str]
    current_agent: Optional[str]
    entities: Dict[str, Any]
    history: List[ConversationTurn]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'user_role': self.user_role.value,
            'state': self.state.value,
            'current_intent': self.current_intent,
            'current_agent': self.current_agent,
            'entities': self.entities,
            'history': [turn.to_dict() for turn in self.history],
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Create from dictionary."""
        return cls(
            session_id=data['session_id'],
            user_id=data['user_id'],
            user_role=UserRole(data['user_role']),
            state=SessionState(data['state']),
            current_intent=data.get('current_intent'),
            current_agent=data.get('current_agent'),
            entities=data.get('entities', {}),
            history=[
                ConversationTurn.from_dict(turn)
                for turn in data.get('history', [])
            ],
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
        )


# ============================================================================
# Conversation Context Manager
# ============================================================================


class ConversationContextManager:
    """
    Manages conversation context and session state using Redis.
    
    Features:
    - Session creation and lifecycle management
    - Conversation history tracking
    - Entity extraction and storage
    - State persistence in Redis
    - Session expiration handling
    
    **Validates: Requirements 3.2, 4.10**
    """
    
    def __init__(
        self,
        redis_client: Optional[Any] = None,
        session_ttl: int = 3600,  # 1 hour default
        enable_logging: bool = True,
    ):
        """
        Initialize conversation context manager.
        
        Args:
            redis_client: Redis client for state storage
            session_ttl: Session time-to-live in seconds
            enable_logging: Enable detailed logging
        """
        self.redis_client = redis_client
        self.session_ttl = session_ttl
        self.enable_logging = enable_logging
        
        # In-memory fallback if Redis not available
        self.memory_store: Dict[str, ConversationContext] = {}
        
        # Statistics
        self.total_sessions = 0
        self.active_sessions = 0
        
        logger.info(
            f"Conversation context manager initialized "
            f"(TTL: {session_ttl}s, Redis: {redis_client is not None})"
        )
    
    async def create_session(
        self,
        user_id: str,
        user_role: UserRole,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConversationContext:
        """
        Create new conversation session.
        
        **Validates: Requirement 3.2**
        
        Args:
            user_id: User identifier
            user_role: User role
            metadata: Optional session metadata
            
        Returns:
            New ConversationContext
        """
        session_id = str(uuid4())
        now = datetime.utcnow()
        
        context = ConversationContext(
            session_id=session_id,
            user_id=user_id,
            user_role=user_role,
            state=SessionState.ACTIVE,
            current_intent=None,
            current_agent=None,
            entities={},
            history=[],
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(seconds=self.session_ttl),
        )
        
        # Store in Redis or memory
        await self._store_context(context)
        
        self.total_sessions += 1
        self.active_sessions += 1
        
        logger.info(f"Created session {session_id} for user {user_id}")
        
        return context
    
    async def get_session(
        self,
        session_id: str,
    ) -> Optional[ConversationContext]:
        """
        Retrieve conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ConversationContext or None if not found/expired
        """
        context = await self._load_context(session_id)
        
        if not context:
            logger.warning(f"Session {session_id} not found")
            return None
        
        # Check expiration
        if context.expires_at < datetime.utcnow():
            logger.info(f"Session {session_id} expired")
            context.state = SessionState.EXPIRED
            await self._store_context(context)
            return None
        
        return context
    
    async def update_session(
        self,
        context: ConversationContext,
    ) -> None:
        """
        Update conversation session.
        
        Args:
            context: Updated conversation context
        """
        context.updated_at = datetime.utcnow()
        await self._store_context(context)
        
        logger.debug(f"Updated session {context.session_id}")
    
    async def add_turn(
        self,
        session_id: str,
        speaker: str,
        content: str,
        agent_type: Optional[str] = None,
        intent: Optional[str] = None,
        confidence: Optional[float] = None,
        actions: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[ConversationContext]:
        """
        Add conversation turn to session.
        
        **Validates: Requirement 4.10**
        
        Args:
            session_id: Session identifier
            speaker: 'user' or 'agent'
            content: Turn content
            agent_type: Optional agent type
            intent: Optional intent
            confidence: Optional confidence score
            actions: Optional list of actions taken
            
        Returns:
            Updated ConversationContext or None if session not found
        """
        context = await self.get_session(session_id)
        
        if not context:
            return None
        
        turn = ConversationTurn(
            turn_id=str(uuid4()),
            speaker=speaker,
            content=content,
            timestamp=datetime.utcnow(),
            agent_type=agent_type,
            intent=intent,
            confidence=confidence,
            actions=actions or [],
        )
        
        context.history.append(turn)
        
        # Update current intent/agent if provided
        if intent:
            context.current_intent = intent
        if agent_type:
            context.current_agent = agent_type
        
        await self.update_session(context)
        
        logger.debug(
            f"Added turn to session {session_id} "
            f"(speaker: {speaker}, intent: {intent})"
        )
        
        return context
    
    async def update_entities(
        self,
        session_id: str,
        entities: Dict[str, Any],
        merge: bool = True,
    ) -> Optional[ConversationContext]:
        """
        Update session entities.
        
        Args:
            session_id: Session identifier
            entities: Entity dictionary
            merge: If True, merge with existing entities; if False, replace
            
        Returns:
            Updated ConversationContext or None if session not found
        """
        context = await self.get_session(session_id)
        
        if not context:
            return None
        
        if merge:
            context.entities.update(entities)
        else:
            context.entities = entities
        
        await self.update_session(context)
        
        logger.debug(f"Updated entities for session {session_id}")
        
        return context
    
    async def set_state(
        self,
        session_id: str,
        state: SessionState,
    ) -> Optional[ConversationContext]:
        """
        Set session state.
        
        Args:
            session_id: Session identifier
            state: New session state
            
        Returns:
            Updated ConversationContext or None if session not found
        """
        context = await self.get_session(session_id)
        
        if not context:
            return None
        
        old_state = context.state
        context.state = state
        
        if state == SessionState.COMPLETED:
            self.active_sessions = max(0, self.active_sessions - 1)
        
        await self.update_session(context)
        
        logger.info(
            f"Session {session_id} state changed: {old_state.value} → {state.value}"
        )
        
        return context
    
    async def extend_session(
        self,
        session_id: str,
        additional_seconds: Optional[int] = None,
    ) -> Optional[ConversationContext]:
        """
        Extend session expiration time.
        
        Args:
            session_id: Session identifier
            additional_seconds: Additional seconds to add (default: session_ttl)
            
        Returns:
            Updated ConversationContext or None if session not found
        """
        context = await self.get_session(session_id)
        
        if not context:
            return None
        
        if additional_seconds is None:
            additional_seconds = self.session_ttl
        
        # Extend from current expiration time, not from now
        context.expires_at = context.expires_at + timedelta(seconds=additional_seconds)
        
        await self.update_session(context)
        
        logger.debug(f"Extended session {session_id} by {additional_seconds}s")
        
        return context
    
    async def delete_session(
        self,
        session_id: str,
    ) -> bool:
        """
        Delete conversation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False if not found
        """
        if self.redis_client:
            try:
                key = f"conversation:{session_id}"
                result = await self.redis_client.delete(key)
                deleted = result > 0
            except Exception as e:
                logger.error(f"Error deleting session from Redis: {e}")
                deleted = False
        else:
            deleted = self.memory_store.pop(session_id, None) is not None
        
        if deleted:
            self.active_sessions = max(0, self.active_sessions - 1)
            logger.info(f"Deleted session {session_id}")
        
        return deleted
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get context manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "session_ttl": self.session_ttl,
            "using_redis": self.redis_client is not None,
            "memory_store_size": len(self.memory_store),
        }
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _store_context(
        self,
        context: ConversationContext,
    ) -> None:
        """Store context in Redis or memory."""
        if self.redis_client:
            try:
                key = f"conversation:{context.session_id}"
                value = json.dumps(context.to_dict())
                await self.redis_client.setex(
                    key,
                    self.session_ttl,
                    value,
                )
            except Exception as e:
                logger.error(f"Error storing context in Redis: {e}")
                # Fallback to memory
                self.memory_store[context.session_id] = context
        else:
            self.memory_store[context.session_id] = context
    
    async def _load_context(
        self,
        session_id: str,
    ) -> Optional[ConversationContext]:
        """Load context from Redis or memory."""
        if self.redis_client:
            try:
                key = f"conversation:{session_id}"
                value = await self.redis_client.get(key)
                
                if value:
                    data = json.loads(value)
                    return ConversationContext.from_dict(data)
            except Exception as e:
                logger.error(f"Error loading context from Redis: {e}")
                # Fallback to memory
                return self.memory_store.get(session_id)
        else:
            return self.memory_store.get(session_id)
        
        return None


# ============================================================================
# Factory Function
# ============================================================================


def create_conversation_context_manager(
    redis_client: Optional[Any] = None,
    session_ttl: int = 3600,
) -> ConversationContextManager:
    """
    Create and configure a conversation context manager.
    
    Args:
        redis_client: Optional Redis client for distributed state
        session_ttl: Session time-to-live in seconds
    
    Returns:
        Configured ConversationContextManager instance
    """
    return ConversationContextManager(
        redis_client=redis_client,
        session_ttl=session_ttl,
    )
