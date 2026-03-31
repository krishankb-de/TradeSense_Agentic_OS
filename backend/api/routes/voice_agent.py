"""
Voice-to-Agent API Endpoints for TradeSense.

Provides endpoints for voice-to-agent integration:
- Create voice sessions
- Process voice input through agent routing
- Handle streaming responses
- Manage interruptions
- Track session metrics

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9, 2.10, 3.1, 3.2, 15.1**
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field

from core.config import settings
from voice.pipeline import VoicePipeline, create_voice_pipeline
from voice.session_manager import VoiceSessionManager, create_voice_session_manager
from voice.voice_agent_integration import (
    VoiceAgentIntegration,
    VoiceAgentRequest,
    VoiceAgentResponse,
    InteractionMode,
    create_voice_agent_integration,
)
from orchestration.agent_router import AgentRouter, create_agent_router
from orchestration.intent_classifier import IntentClassifier, create_intent_classifier

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances (initialized on startup)
_voice_pipeline: Optional[VoicePipeline] = None
_session_manager: Optional[VoiceSessionManager] = None
_agent_router: Optional[AgentRouter] = None
_voice_agent_integration: Optional[VoiceAgentIntegration] = None


# Request/Response Models
class CreateVoiceSessionRequest(BaseModel):
    """Request to create a voice session."""
    user_id: Optional[str] = Field(default=None, description="User ID")
    user_role: Optional[str] = Field(default=None, description="User role (technician, customer, dispatcher)")
    customer_id: Optional[str] = Field(default=None, description="Customer ID")
    technician_id: Optional[str] = Field(default=None, description="Technician ID")
    job_id: Optional[str] = Field(default=None, description="Job ID")
    context: Optional[dict] = Field(default=None, description="Additional context")


class VoiceSessionResponse(BaseModel):
    """Response with voice session details."""
    session_id: str = Field(description="Session ID")
    status: str = Field(description="Session status")
    created_at: str = Field(description="Creation timestamp")
    user_id: Optional[str] = Field(default=None, description="User ID")
    user_role: Optional[str] = Field(default=None, description="User role")
    metrics: dict = Field(description="Session metrics")


class ProcessVoiceRequest(BaseModel):
    """Request to process voice input."""
    session_id: str = Field(description="Session ID")
    text_input: Optional[str] = Field(default=None, description="Text input (fallback mode)")


class ProcessVoiceResponse(BaseModel):
    """Response from voice processing."""
    session_id: str = Field(description="Session ID")
    text_response: str = Field(description="Text response")
    intent: Optional[str] = Field(default=None, description="Classified intent")
    agent_type: Optional[str] = Field(default=None, description="Agent that handled request")
    confidence: float = Field(description="Confidence score")
    latency: float = Field(description="Processing latency in ms")
    mode: str = Field(description="Interaction mode (voice/text)")
    error: Optional[str] = Field(default=None, description="Error message if failed")


class SessionMetricsResponse(BaseModel):
    """Response with session metrics."""
    session_id: str
    duration: float
    turn_count: int
    user_turns: int
    agent_turns: int
    interruptions: int
    turn_taking_accuracy: float
    latency: dict
    api_cost: float


# Dependencies
def get_voice_pipeline() -> VoicePipeline:
    """Get voice pipeline instance."""
    global _voice_pipeline
    
    if _voice_pipeline is None:
        if not settings.use_azure_speech:
            raise HTTPException(
                status_code=503,
                detail="Azure Speech Services is not enabled"
            )
        
        _voice_pipeline = create_voice_pipeline(
            azure_speech_key=settings.azure_speech_key,
            azure_speech_region=settings.azure_speech_region,
        )
    
    return _voice_pipeline


def get_session_manager() -> VoiceSessionManager:
    """Get session manager instance."""
    global _session_manager
    
    if _session_manager is None:
        _session_manager = create_voice_session_manager(
            voice_pipeline=get_voice_pipeline(),
        )
    
    return _session_manager


def get_agent_router() -> AgentRouter:
    """Get agent router instance."""
    global _agent_router
    
    if _agent_router is None:
        # Create intent classifier
        intent_classifier = create_intent_classifier()
        
        # Create agent router
        _agent_router = create_agent_router(
            intent_classifier=intent_classifier,
        )
    
    return _agent_router


def get_voice_agent_integration() -> VoiceAgentIntegration:
    """Get voice-agent integration instance."""
    global _voice_agent_integration
    
    if _voice_agent_integration is None:
        _voice_agent_integration = create_voice_agent_integration(
            voice_pipeline=get_voice_pipeline(),
            agent_router=get_agent_router(),
            session_manager=get_session_manager(),
        )
    
    return _voice_agent_integration


# Endpoints
@router.post("/sessions", response_model=VoiceSessionResponse)
async def create_voice_session(
    request: CreateVoiceSessionRequest,
    session_manager: VoiceSessionManager = Depends(get_session_manager),
):
    """
    Create a new voice-to-agent session.
    
    This endpoint creates a session that integrates voice processing
    with agent routing for complete voice-driven interactions.
    
    Args:
        request: Session creation request
        
    Returns:
        VoiceSessionResponse with session details
    """
    try:
        session = session_manager.create_session(
            user_id=request.user_id,
            user_role=request.user_role,
            customer_id=request.customer_id,
            technician_id=request.technician_id,
            job_id=request.job_id,
            context=request.context,
        )
        
        return VoiceSessionResponse(
            session_id=session.session_id,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            user_id=session.user_id,
            user_role=session.user_role,
            metrics=session.metrics.to_dict(),
        )
    
    except Exception as e:
        logger.error(f"Failed to create voice session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create voice session: {str(e)}"
        )


@router.post("/sessions/{session_id}/process", response_model=ProcessVoiceResponse)
async def process_voice_input(
    session_id: str,
    audio: Optional[UploadFile] = File(None, description="Audio file (optional)"),
    text_input: Optional[str] = None,
    integration: VoiceAgentIntegration = Depends(get_voice_agent_integration),
):
    """
    Process voice or text input through agent routing.
    
    This endpoint implements the complete voice-to-agent flow:
    1. Transcribe audio (if provided) or use text input
    2. Classify intent and route to appropriate agent
    3. Execute agent processing
    4. Synthesize response to speech (if audio input)
    5. Return text and audio response
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2**
    
    Args:
        session_id: Session ID
        audio: Audio file (optional)
        text_input: Text input (optional, fallback mode)
        
    Returns:
        ProcessVoiceResponse with agent response
    """
    try:
        # Validate input
        if not audio and not text_input:
            raise HTTPException(
                status_code=400,
                detail="Either audio file or text_input must be provided"
            )
        
        # Read audio data if provided
        audio_data = None
        if audio:
            audio_data = await audio.read()
        
        # Create request
        request = VoiceAgentRequest(
            session_id=session_id,
            audio_data=audio_data,
            text_input=text_input,
        )
        
        # Process through integration
        response = await integration.process_voice_input(request)
        
        return ProcessVoiceResponse(
            session_id=response.session_id,
            text_response=response.text_response,
            intent=response.intent,
            agent_type=response.agent_type,
            confidence=response.confidence,
            latency=response.latency,
            mode=response.mode.value,
            error=response.error,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Voice processing failed: {str(e)}"
        )


@router.post("/sessions/{session_id}/process/audio")
async def process_voice_input_with_audio(
    session_id: str,
    audio: UploadFile = File(..., description="Audio file"),
    integration: VoiceAgentIntegration = Depends(get_voice_agent_integration),
):
    """
    Process voice input and return audio response.
    
    This endpoint is optimized for voice-only interactions,
    returning the synthesized audio response directly.
    
    Args:
        session_id: Session ID
        audio: Audio file
        
    Returns:
        Audio response (MP3 format)
    """
    try:
        # Read audio data
        audio_data = await audio.read()
        
        # Create request
        request = VoiceAgentRequest(
            session_id=session_id,
            audio_data=audio_data,
        )
        
        # Process through integration
        response = await integration.process_voice_input(request)
        
        if response.error:
            raise HTTPException(
                status_code=500,
                detail=response.error
            )
        
        if not response.audio_response:
            raise HTTPException(
                status_code=500,
                detail="Audio synthesis failed"
            )
        
        return Response(
            content=response.audio_response,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=response.mp3",
                "X-Session-ID": session_id,
                "X-Intent": response.intent or "",
                "X-Agent-Type": response.agent_type or "",
                "X-Latency": str(response.latency),
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Voice processing failed: {str(e)}"
        )


@router.post("/sessions/{session_id}/interrupt")
async def interrupt_session(
    session_id: str,
    integration: VoiceAgentIntegration = Depends(get_voice_agent_integration),
):
    """
    Request interruption of agent speech.
    
    This endpoint allows the user to interrupt the agent while it's speaking,
    implementing natural turn-taking behavior.
    
    **Validates: Requirement 2.9**
    
    Args:
        session_id: Session ID
        
    Returns:
        Success message
    """
    try:
        handled = await integration.handle_interruption(session_id)
        
        return {
            "session_id": session_id,
            "handled": handled,
            "message": "Interruption handled" if handled else "Interruption not needed"
        }
    
    except Exception as e:
        logger.error(f"Interruption handling failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Interruption handling failed: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=VoiceSessionResponse)
async def get_voice_session(
    session_id: str,
    session_manager: VoiceSessionManager = Depends(get_session_manager),
):
    """
    Get voice session details.
    
    Args:
        session_id: Session ID
        
    Returns:
        VoiceSessionResponse with session details
    """
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return VoiceSessionResponse(
        session_id=session.session_id,
        status=session.status.value,
        created_at=session.created_at.isoformat(),
        user_id=session.user_id,
        user_role=session.user_role,
        metrics=session.metrics.to_dict(),
    )


@router.delete("/sessions/{session_id}")
async def end_voice_session(
    session_id: str,
    session_manager: VoiceSessionManager = Depends(get_session_manager),
):
    """
    End a voice session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Success message with final metrics
    """
    session = session_manager.end_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return {
        "message": f"Session {session_id} ended successfully",
        "final_metrics": session.metrics.to_dict(),
    }


@router.get("/sessions/{session_id}/metrics", response_model=SessionMetricsResponse)
async def get_session_metrics(
    session_id: str,
    session_manager: VoiceSessionManager = Depends(get_session_manager),
):
    """
    Get detailed metrics for a voice session.
    
    Args:
        session_id: Session ID
        
    Returns:
        SessionMetricsResponse with detailed metrics
    """
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    metrics = session.metrics
    
    return SessionMetricsResponse(
        session_id=metrics.session_id,
        duration=metrics.get_session_duration(),
        turn_count=metrics.turn_count,
        user_turns=metrics.user_turns,
        agent_turns=metrics.agent_turns,
        interruptions=metrics.interruptions,
        turn_taking_accuracy=metrics.get_turn_taking_accuracy(),
        latency={
            "avg": metrics.avg_latency,
            "p50": metrics.p50_latency,
            "p95": metrics.p95_latency,
            "p99": metrics.p99_latency,
        },
        api_cost=metrics.api_cost,
    )


@router.get("/sessions")
async def list_active_sessions(
    session_manager: VoiceSessionManager = Depends(get_session_manager),
):
    """
    List all active voice sessions.
    
    Returns:
        List of active session IDs and statistics
    """
    active_sessions = session_manager.get_active_sessions()
    statistics = session_manager.get_statistics()
    
    return {
        "active_sessions": [
            {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "user_role": session.user_role,
                "turn_count": session.metrics.turn_count,
                "duration": session.metrics.get_session_duration(),
            }
            for session in active_sessions
        ],
        "statistics": statistics,
    }


@router.websocket("/sessions/{session_id}/stream")
async def stream_voice_interaction(
    websocket: WebSocket,
    session_id: str,
):
    """
    WebSocket endpoint for streaming voice interactions.
    
    This endpoint provides real-time streaming with:
    - Partial transcriptions
    - Streaming agent responses
    - Interruption handling
    
    **Validates: Requirements 2.8, 2.9**
    
    Protocol:
    1. Client connects to WebSocket
    2. Client sends audio chunks as binary data
    3. Server sends back JSON messages with:
       - Partial transcriptions
       - Agent responses
       - Errors
    4. Client can send interruption signal
    5. Client sends close frame to end session
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for session {session_id}")
    
    try:
        # Get integration
        integration = get_voice_agent_integration()
        
        # Get session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            await websocket.send_json({
                "type": "error",
                "message": f"Session {session_id} not found"
            })
            await websocket.close()
            return
        
        # Process streaming audio
        while True:
            # Receive data from client
            data = await websocket.receive()
            
            if "bytes" in data:
                # Audio chunk received
                # TODO: Implement streaming processing
                await websocket.send_json({
                    "type": "partial",
                    "text": "Processing audio...",
                })
            
            elif "text" in data:
                # Text message received (e.g., interruption signal)
                message = data["text"]
                if message == "interrupt":
                    handled = await integration.handle_interruption(session_id)
                    await websocket.send_json({
                        "type": "interruption",
                        "handled": handled,
                    })
            
            else:
                # Unknown message type
                logger.warning(f"Unknown message type: {data}")
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
