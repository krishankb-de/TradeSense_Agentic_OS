"""
WebRTC Signaling Server
Handles WebRTC peer connection signaling for voice interactions
Validates: Requirements 4.1, 11.5
"""

import logging
import asyncio
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class SignalingMessageType(str, Enum):
    """WebRTC signaling message types."""
    OFFER = "offer"
    ANSWER = "answer"
    ICE_CANDIDATE = "ice-candidate"
    CLOSE = "close"


@dataclass
class SignalingMessage:
    """WebRTC signaling message."""
    type: SignalingMessageType
    peer_id: str
    session_id: str
    payload: Dict[str, Any]
    timestamp: datetime


class WebRTCSignalingServer:
    """
    WebRTC Signaling Server for voice interactions.
    
    Handles peer connection establishment, ICE candidate exchange,
    and session management for WebRTC-based voice calls.
    
    Features:
    - SDP offer/answer exchange
    - ICE candidate relay
    - Session lifecycle management
    - Connection state tracking
    
    Validates: Requirements 4.1, 11.5
    """
    
    def __init__(self):
        """Initialize WebRTC signaling server."""
        # Active sessions: session_id -> peer_connection_info
        self.sessions: Dict[str, Dict[str, Any]] = {}
        
        # Peer connections: peer_id -> websocket
        self.peers: Dict[str, Any] = {}
        
        # Message handlers
        self.on_offer: Optional[Callable] = None
        self.on_answer: Optional[Callable] = None
        self.on_ice_candidate: Optional[Callable] = None
        self.on_session_close: Optional[Callable] = None
        
        logger.info("WebRTC Signaling Server initialized")
    
    async def handle_message(
        self,
        peer_id: str,
        message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle incoming signaling message from peer.
        
        Args:
            peer_id: Unique peer identifier
            message: Signaling message payload
            
        Returns:
            Response message if applicable
        """
        try:
            msg_type = SignalingMessageType(message.get('type'))
            session_id = message.get('session_id')
            payload = message.get('payload', {})
            
            signaling_msg = SignalingMessage(
                type=msg_type,
                peer_id=peer_id,
                session_id=session_id,
                payload=payload,
                timestamp=datetime.utcnow()
            )
            
            logger.info(
                f"Received {msg_type.value} from peer {peer_id} "
                f"for session {session_id}"
            )
            
            # Route to appropriate handler
            if msg_type == SignalingMessageType.OFFER:
                return await self._handle_offer(signaling_msg)
            elif msg_type == SignalingMessageType.ANSWER:
                return await self._handle_answer(signaling_msg)
            elif msg_type == SignalingMessageType.ICE_CANDIDATE:
                return await self._handle_ice_candidate(signaling_msg)
            elif msg_type == SignalingMessageType.CLOSE:
                return await self._handle_close(signaling_msg)
            else:
                logger.warning(f"Unknown message type: {msg_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error handling signaling message: {e}")
            return {
                'type': 'error',
                'error': str(e)
            }
    
    async def _handle_offer(
        self,
        message: SignalingMessage
    ) -> Dict[str, Any]:
        """
        Handle SDP offer from peer.
        
        Args:
            message: Signaling message with SDP offer
            
        Returns:
            Response with session info
        """
        session_id = message.session_id
        peer_id = message.peer_id
        sdp = message.payload.get('sdp')
        
        if not sdp:
            raise ValueError("SDP offer missing from payload")
        
        # Create session
        self.sessions[session_id] = {
            'peer_id': peer_id,
            'state': 'offer-received',
            'offer_sdp': sdp,
            'created_at': datetime.utcnow(),
            'ice_candidates': []
        }
        
        logger.info(f"Created session {session_id} for peer {peer_id}")
        
        # Call external handler if registered
        if self.on_offer:
            await self.on_offer(message)
        
        return {
            'type': 'offer-received',
            'session_id': session_id,
            'status': 'success'
        }
    
    async def _handle_answer(
        self,
        message: SignalingMessage
    ) -> Dict[str, Any]:
        """
        Handle SDP answer from peer.
        
        Args:
            message: Signaling message with SDP answer
            
        Returns:
            Response confirming answer
        """
        session_id = message.session_id
        sdp = message.payload.get('sdp')
        
        if not sdp:
            raise ValueError("SDP answer missing from payload")
        
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        # Update session
        self.sessions[session_id]['answer_sdp'] = sdp
        self.sessions[session_id]['state'] = 'connected'
        
        logger.info(f"Session {session_id} connected")
        
        # Call external handler if registered
        if self.on_answer:
            await self.on_answer(message)
        
        return {
            'type': 'answer-received',
            'session_id': session_id,
            'status': 'connected'
        }
    
    async def _handle_ice_candidate(
        self,
        message: SignalingMessage
    ) -> Dict[str, Any]:
        """
        Handle ICE candidate from peer.
        
        Args:
            message: Signaling message with ICE candidate
            
        Returns:
            Response confirming candidate
        """
        session_id = message.session_id
        candidate = message.payload.get('candidate')
        
        if not candidate:
            raise ValueError("ICE candidate missing from payload")
        
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        # Store ICE candidate
        self.sessions[session_id]['ice_candidates'].append({
            'candidate': candidate,
            'timestamp': datetime.utcnow()
        })
        
        logger.debug(
            f"Added ICE candidate for session {session_id}: "
            f"{candidate.get('candidate', '')[:50]}..."
        )
        
        # Call external handler if registered
        if self.on_ice_candidate:
            await self.on_ice_candidate(message)
        
        return {
            'type': 'ice-candidate-received',
            'session_id': session_id,
            'status': 'success'
        }
    
    async def _handle_close(
        self,
        message: SignalingMessage
    ) -> Dict[str, Any]:
        """
        Handle session close from peer.
        
        Args:
            message: Signaling message to close session
            
        Returns:
            Response confirming closure
        """
        session_id = message.session_id
        
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session['state'] = 'closed'
            session['closed_at'] = datetime.utcnow()
            
            logger.info(f"Session {session_id} closed")
            
            # Call external handler if registered
            if self.on_session_close:
                await self.on_session_close(message)
            
            # Remove session after delay
            asyncio.create_task(self._cleanup_session(session_id, delay=60))
        
        return {
            'type': 'session-closed',
            'session_id': session_id,
            'status': 'success'
        }
    
    async def _cleanup_session(self, session_id: str, delay: int = 60):
        """
        Clean up session after delay.
        
        Args:
            session_id: Session to clean up
            delay: Delay in seconds before cleanup
        """
        await asyncio.sleep(delay)
        
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleaned up session {session_id}")
    
    async def create_answer(
        self,
        session_id: str,
        answer_sdp: str
    ) -> Dict[str, Any]:
        """
        Create SDP answer for a session.
        
        Args:
            session_id: Session identifier
            answer_sdp: SDP answer string
            
        Returns:
            Answer message to send to peer
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.sessions[session_id]
        session['answer_sdp'] = answer_sdp
        session['state'] = 'answer-created'
        
        return {
            'type': 'answer',
            'session_id': session_id,
            'payload': {
                'sdp': answer_sdp
            }
        }
    
    async def add_ice_candidate(
        self,
        session_id: str,
        candidate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add ICE candidate for a session.
        
        Args:
            session_id: Session identifier
            candidate: ICE candidate data
            
        Returns:
            ICE candidate message to send to peer
        """
        if session_id not in self.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        return {
            'type': 'ice-candidate',
            'session_id': session_id,
            'payload': {
                'candidate': candidate
            }
        }
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data if found, None otherwise
        """
        return self.sessions.get(session_id)
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all active sessions.
        
        Returns:
            Dictionary of active sessions
        """
        return {
            sid: session
            for sid, session in self.sessions.items()
            if session.get('state') != 'closed'
        }
    
    def set_handlers(
        self,
        on_offer: Optional[Callable] = None,
        on_answer: Optional[Callable] = None,
        on_ice_candidate: Optional[Callable] = None,
        on_session_close: Optional[Callable] = None
    ):
        """
        Set event handlers for signaling events.
        
        Args:
            on_offer: Handler for SDP offers
            on_answer: Handler for SDP answers
            on_ice_candidate: Handler for ICE candidates
            on_session_close: Handler for session closures
        """
        self.on_offer = on_offer
        self.on_answer = on_answer
        self.on_ice_candidate = on_ice_candidate
        self.on_session_close = on_session_close


# Factory function
def create_webrtc_signaling_server() -> WebRTCSignalingServer:
    """
    Factory function to create WebRTC signaling server.
    
    Returns:
        Configured WebRTCSignalingServer instance
    """
    return WebRTCSignalingServer()
