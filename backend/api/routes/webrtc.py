"""
WebRTC Signaling API Endpoints
Handles WebRTC peer connection signaling for voice sessions

Validates: Requirements 4.1, 11.5
"""

import logging
from typing import Dict, Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from notifications.webrtc_signaling import (
    create_webrtc_signaling_server,
    WebRTCSignalingServer,
    SignalingMessageType
)
from security.auth import get_current_user, User

logger = logging.getLogger(__name__)

router = APIRouter()

# Global signaling server instance
_signaling_server: Optional[WebRTCSignalingServer] = None


def get_signaling_server() -> WebRTCSignalingServer:
    """
    Get or create WebRTC signaling server instance.
    
    Returns:
        WebRTCSignalingServer instance
    """
    global _signaling_server
    
    if _signaling_server is None:
        _signaling_server = create_webrtc_signaling_server()
        logger.info("WebRTC signaling server initialized")
    
    return _signaling_server


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateSessionRequest(BaseModel):
    """Request model for creating WebRTC session."""
    sdp: str = Field(..., description="SDP offer")


class CreateSessionResponse(BaseModel):
    """Response model for creating WebRTC session."""
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Session status")


class AnswerRequest(BaseModel):
    """Request model for SDP answer."""
    sdp: str = Field(..., description="SDP answer")


class AnswerResponse(BaseModel):
    """Response model for SDP answer."""
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Connection status")


class ICECandidateRequest(BaseModel):
    """Request model for ICE candidate."""
    candidate: Dict[str, Any] = Field(..., description="ICE candidate data")


class ICECandidateResponse(BaseModel):
    """Response model for ICE candidate."""
    session_id: str = Field(..., description="Session ID")
    status: str = Field(..., description="Status")


class SessionInfoResponse(BaseModel):
    """Response model for session info."""
    session_id: str
    peer_id: str
    state: str
    created_at: str
    ice_candidates_count: int


# ============================================================================
# REST API Endpoints
# ============================================================================

@router.post(
    "/sessions",
    response_model=CreateSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create WebRTC session",
    description="Create new WebRTC session with SDP offer"
)
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    signaling_server: WebRTCSignalingServer = Depends(get_signaling_server)
):
    """
    Create new WebRTC session with SDP offer.
    
    Validates: Requirement 4.1 (WebRTC voice interactions)
    Validates: Requirement 11.5 (WebRTC signaling)
    """
    try:
        # Generate session ID
        session_id = str(uuid4())
        peer_id = current_user.id
        
        # Handle offer
        message = {
            'type': SignalingMessageType.OFFER.value,
            'session_id': session_id,
            'payload': {
                'sdp': request.sdp
            }
        }
        
        response = await signaling_server.handle_message(peer_id, message)
        
        return CreateSessionResponse(
            session_id=session_id,
            status=response.get('status', 'created')
        )
        
    except Exception as e:
        logger.error(f"Failed to create WebRTC session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create WebRTC session: {str(e)}"
        )


@router.post(
    "/sessions/{session_id}/answer",
    response_model=AnswerResponse,
    summary="Send SDP answer",
    description="Send SDP answer for WebRTC session"
)
async def send_answer(
    session_id: str,
    request: AnswerRequest,
    current_user: User = Depends(get_current_user),
    signaling_server: WebRTCSignalingServer = Depends(get_signaling_server)
):
    """
    Send SDP answer for WebRTC session.
    
    Validates: Requirement 4.1 (WebRTC voice interactions)
    """
    try:
        peer_id = current_user.id
        
        # Handle answer
        message = {
            'type': SignalingMessageType.ANSWER.value,
            'session_id': session_id,
            'payload': {
                'sdp': request.sdp
            }
        }
        
        response = await signaling_server.handle_message(peer_id, message)
        
        return AnswerResponse(
            session_id=session_id,
            status=response.get('status', 'connected')
        )
        
    except Exception as e:
        logger.error(f"Failed to send SDP answer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send SDP answer: {str(e)}"
        )


@router.post(
    "/sessions/{session_id}/ice-candidate",
    response_model=ICECandidateResponse,
    summary="Add ICE candidate",
    description="Add ICE candidate for WebRTC session"
)
async def add_ice_candidate(
    session_id: str,
    request: ICECandidateRequest,
    current_user: User = Depends(get_current_user),
    signaling_server: WebRTCSignalingServer = Depends(get_signaling_server)
):
    """
    Add ICE candidate for WebRTC session.
    
    Validates: Requirement 4.1 (WebRTC voice interactions)
    """
    try:
        peer_id = current_user.id
        
        # Handle ICE candidate
        message = {
            'type': SignalingMessageType.ICE_CANDIDATE.value,
            'session_id': session_id,
            'payload': {
                'candidate': request.candidate
            }
        }
        
        response = await signaling_server.handle_message(peer_id, message)
        
        return ICECandidateResponse(
            session_id=session_id,
            status=response.get('status', 'success')
        )
        
    except Exception as e:
        logger.error(f"Failed to add ICE candidate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add ICE candidate: {str(e)}"
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionInfoResponse,
    summary="Get session info",
    description="Get WebRTC session information"
)
async def get_session_info(
    session_id: str,
    current_user: User = Depends(get_current_user),
    signaling_server: WebRTCSignalingServer = Depends(get_signaling_server)
):
    """
    Get WebRTC session information.
    
    Validates: Requirement 4.1 (WebRTC voice interactions)
    """
    try:
        session = signaling_server.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return SessionInfoResponse(
            session_id=session_id,
            peer_id=session.get('peer_id'),
            state=session.get('state'),
            created_at=session.get('created_at').isoformat(),
            ice_candidates_count=len(session.get('ice_candidates', []))
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session info: {str(e)}"
        )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Close session",
    description="Close WebRTC session"
)
async def close_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    signaling_server: WebRTCSignalingServer = Depends(get_signaling_server)
):
    """
    Close WebRTC session.
    
    Validates: Requirement 4.1 (WebRTC voice interactions)
    """
    try:
        peer_id = current_user.id
        
        # Handle close
        message = {
            'type': SignalingMessageType.CLOSE.value,
            'session_id': session_id,
            'payload': {}
        }
        
        await signaling_server.handle_message(peer_id, message)
        
        logger.info(f"WebRTC session {session_id} closed by user {current_user.id}")
        
    except Exception as e:
        logger.error(f"Failed to close session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to close session: {str(e)}"
        )


@router.get(
    "/sessions",
    summary="List active sessions",
    description="Get list of active WebRTC sessions"
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    signaling_server: WebRTCSignalingServer = Depends(get_signaling_server)
):
    """
    List active WebRTC sessions.
    
    Validates: Requirement 4.1 (WebRTC voice interactions)
    """
    try:
        sessions = signaling_server.get_active_sessions()
        
        return {
            'sessions': [
                {
                    'session_id': sid,
                    'peer_id': session.get('peer_id'),
                    'state': session.get('state'),
                    'created_at': session.get('created_at').isoformat()
                }
                for sid, session in sessions.items()
            ],
            'total': len(sessions)
        }
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sessions: {str(e)}"
        )


# ============================================================================
# WebSocket Signaling Endpoint
# ============================================================================

@router.websocket("/ws/{session_id}")
async def websocket_signaling(
    websocket: WebSocket,
    session_id: str
):
    """
    WebSocket endpoint for WebRTC signaling.
    
    This provides an alternative to REST API for real-time signaling.
    
    Protocol:
    1. Client connects with session ID
    2. Client sends/receives signaling messages (offer, answer, ICE candidates)
    3. Messages are relayed between peers
    
    Validates: Requirement 4.1 (WebRTC voice interactions)
    """
    await websocket.accept()
    
    signaling_server = get_signaling_server()
    
    logger.info(f"WebSocket signaling connected for session {session_id}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Handle signaling message
            response = await signaling_server.handle_message(
                peer_id=data.get('peer_id', 'unknown'),
                message=data
            )
            
            # Send response back to client
            if response:
                await websocket.send_json(response)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket signaling disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket signaling error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
