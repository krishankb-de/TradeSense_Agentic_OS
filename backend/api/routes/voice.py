"""
Voice processing API endpoints
Provides STT and TTS services using Azure Speech Services
"""

import logging
import time
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field
import azure.cognitiveservices.speech as speechsdk

from core.config import settings
from voice.stt import AzureSpeechSTT, TranscriptionResult, create_azure_stt
from voice.tts import AzureSpeechTTS, VoiceConfig, VoiceStyle, create_azure_tts
from voice.pipeline import (
    VoicePipeline,
    VoicePipelineConfig,
    VoiceSession,
    SessionState,
    create_voice_pipeline,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Global pipeline instance (initialized on startup)
_pipeline: Optional[VoicePipeline] = None


# Request/Response Models
class TranscribeRequest(BaseModel):
    """Request model for audio transcription."""
    language: Optional[str] = Field(
        default="en-US",
        description="Language code for speech recognition"
    )
    enable_profanity_filter: bool = Field(
        default=True,
        description="Enable profanity filtering"
    )
    enable_dictation: bool = Field(
        default=True,
        description="Enable dictation mode for better punctuation"
    )


class TranscribeResponse(BaseModel):
    """Response model for audio transcription."""
    text: str = Field(description="Transcribed text")
    confidence: float = Field(description="Confidence score (0-1)")
    duration: float = Field(description="Audio duration in seconds")
    latency: float = Field(description="Processing latency in milliseconds")
    language: str = Field(description="Recognition language used")


class StreamTranscribeResponse(BaseModel):
    """Response model for streaming transcription chunks."""
    text: str = Field(description="Transcribed text chunk")
    is_final: bool = Field(description="Whether this is a final result")
    confidence: float = Field(description="Confidence score (0-1)")
    timestamp: float = Field(description="Timestamp in seconds")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    azure_speech_configured: bool
    supported_languages: list[str]


class SynthesizeRequest(BaseModel):
    """Request model for text-to-speech synthesis."""
    text: str = Field(description="Text to synthesize", min_length=1, max_length=5000)
    voice_name: Optional[str] = Field(
        default=None,
        description="Neural voice name (e.g., 'en-US-JennyNeural')"
    )
    style: Optional[VoiceStyle] = Field(
        default=VoiceStyle.NEUTRAL,
        description="Voice style (neutral, cheerful, empathetic, etc.)"
    )
    pitch: Optional[str] = Field(
        default="+0%",
        description="Pitch adjustment (-50% to +50%)"
    )
    rate: Optional[str] = Field(
        default="+0%",
        description="Speaking rate adjustment (-50% to +200%)"
    )
    volume: Optional[str] = Field(
        default="+0%",
        description="Volume adjustment (-50% to +50%)"
    )


class SynthesizeResponse(BaseModel):
    """Response model for text-to-speech synthesis."""
    success: bool = Field(description="Whether synthesis succeeded")
    duration: float = Field(description="Audio duration in seconds")
    latency: float = Field(description="Processing latency in milliseconds")
    voice_name: str = Field(description="Voice used for synthesis")
    audio_size: int = Field(description="Audio data size in bytes")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class VoicesResponse(BaseModel):
    """Response model for available voices."""
    voices: list[str] = Field(description="List of available neural voices")
    default_voice: str = Field(description="Default voice name")
    language: Optional[str] = Field(default=None, description="Language filter applied")


class SessionCreateRequest(BaseModel):
    """Request model for creating a voice session."""
    context: Optional[dict] = Field(default=None, description="Optional session context")


class SessionResponse(BaseModel):
    """Response model for voice session."""
    session_id: str = Field(description="Session ID")
    state: str = Field(description="Current session state")
    turn_state: str = Field(description="Current turn state")
    created_at: str = Field(description="Session creation timestamp")
    metrics: dict = Field(description="Session metrics")


class SessionMetricsResponse(BaseModel):
    """Response model for session metrics."""
    session_id: str
    duration: float
    turn_count: int
    user_turns: int
    agent_turns: int
    interruptions: int
    turn_taking_accuracy: float
    avg_latency: float


# Dependency to get pipeline instance
def get_pipeline() -> VoicePipeline:
    """
    Get voice pipeline instance.
    
    Returns:
        VoicePipeline instance
        
    Raises:
        HTTPException: If pipeline is not initialized
    """
    global _pipeline
    
    if _pipeline is None:
        # Initialize pipeline on first use
        if not settings.use_azure_speech:
            raise HTTPException(
                status_code=503,
                detail="Azure Speech Services is not enabled. Set USE_AZURE_SPEECH=true in .env"
            )
        
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise HTTPException(
                status_code=503,
                detail="Azure Speech Services credentials not configured. "
                       "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env"
            )
        
        try:
            _pipeline = create_voice_pipeline(
                azure_speech_key=settings.azure_speech_key,
                azure_speech_region=settings.azure_speech_region,
                stt_language=settings.azure_speech_language,
                tts_voice_name=settings.azure_speech_voice,
            )
            logger.info("Voice pipeline initialized")
        except Exception as e:
            logger.error(f"Failed to initialize voice pipeline: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"Failed to initialize voice pipeline: {str(e)}"
            )
    
    return _pipeline


# Dependency to get STT client
def get_stt_client() -> AzureSpeechSTT:
    """
    Get configured Azure Speech STT client.
    
    Returns:
        AzureSpeechSTT instance
        
    Raises:
        HTTPException: If Azure Speech is not configured
    """
    if not settings.use_azure_speech:
        raise HTTPException(
            status_code=503,
            detail="Azure Speech Services is not enabled. Set USE_AZURE_SPEECH=true in .env"
        )
    
    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise HTTPException(
            status_code=503,
            detail="Azure Speech Services credentials not configured. "
                   "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env"
        )
    
    try:
        return create_azure_stt(
            subscription_key=settings.azure_speech_key,
            region=settings.azure_speech_region,
            language=settings.azure_speech_language,
        )
    except Exception as e:
        logger.error(f"Failed to create Azure Speech STT client: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize Azure Speech Services: {str(e)}"
        )


# Dependency to get TTS client
def get_tts_client() -> AzureSpeechTTS:
    """
    Get configured Azure Speech TTS client.
    
    Returns:
        AzureSpeechTTS instance
        
    Raises:
        HTTPException: If Azure Speech is not configured
    """
    if not settings.use_azure_speech:
        raise HTTPException(
            status_code=503,
            detail="Azure Speech Services is not enabled. Set USE_AZURE_SPEECH=true in .env"
        )
    
    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise HTTPException(
            status_code=503,
            detail="Azure Speech Services credentials not configured. "
                   "Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in .env"
        )
    
    try:
        return create_azure_tts(
            subscription_key=settings.azure_speech_key,
            region=settings.azure_speech_region,
            voice_name=settings.azure_speech_voice,
        )
    except Exception as e:
        logger.error(f"Failed to create Azure Speech TTS client: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Failed to initialize Azure Speech Services: {str(e)}"
        )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(stt: AzureSpeechSTT = Depends(get_stt_client)):
    """
    Health check endpoint for voice services.
    
    Returns:
        Health status and configuration info
    """
    return HealthCheckResponse(
        status="healthy",
        azure_speech_configured=settings.use_azure_speech,
        supported_languages=stt.get_supported_languages()
    )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file to transcribe (WAV format recommended)"),
    language: str = "en-US",
    enable_profanity_filter: bool = True,
    enable_dictation: bool = True,
    stt: AzureSpeechSTT = Depends(get_stt_client)
):
    """
    Transcribe audio file to text.
    
    This endpoint accepts an audio file and returns the transcribed text.
    Optimized for <500ms first-token latency.
    
    Args:
        audio: Audio file (WAV, MP3, OGG formats supported)
        language: Language code (e.g., 'en-US', 'es-ES')
        enable_profanity_filter: Enable profanity filtering
        enable_dictation: Enable dictation mode for better punctuation
        
    Returns:
        TranscribeResponse with transcribed text and metadata
        
    Raises:
        HTTPException: If transcription fails
    """
    start_time = time.time()
    
    try:
        # Validate file type
        if not audio.content_type or not audio.content_type.startswith("audio/"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {audio.content_type}. Expected audio file."
            )
        
        # Save uploaded file temporarily
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Update STT client settings if needed
            if language != stt.language:
                stt.set_language(language)
            
            # Create audio config from file
            audio_config = stt.create_audio_config_from_file(temp_file_path)
            
            # Transcribe
            logger.info(f"Transcribing audio file: {audio.filename} ({len(content)} bytes)")
            result = await stt.transcribe_once(audio_config=audio_config)
            
            # Calculate latency
            latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            logger.info(
                f"Transcription complete: text_length={len(result.text)}, "
                f"latency={latency:.2f}ms, confidence={result.confidence}"
            )
            
            # Check latency target
            if latency > 500:
                logger.warning(
                    f"Transcription latency ({latency:.2f}ms) exceeded target (500ms)"
                )
            
            return TranscribeResponse(
                text=result.text,
                confidence=result.confidence,
                duration=result.duration,
                latency=latency,
                language=language
            )
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )


@router.websocket("/transcribe/stream")
async def transcribe_stream(websocket: WebSocket):
    """
    WebSocket endpoint for streaming audio transcription.
    
    This endpoint provides real-time streaming transcription with:
    - Partial results (recognizing events)
    - Final results (recognized events)
    - <500ms first-token latency
    
    Protocol:
    1. Client connects to WebSocket
    2. Client sends audio chunks as binary data
    3. Server sends back JSON messages with transcription results:
       - {"type": "partial", "text": "...", "confidence": 0.8}
       - {"type": "final", "text": "...", "confidence": 0.95}
       - {"type": "error", "message": "..."}
    4. Client sends close frame to end session
    
    Example client code:
        const ws = new WebSocket('ws://localhost:8000/api/v1/voice/transcribe/stream');
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data.type, data.text);
        };
        // Send audio chunks
        ws.send(audioChunk);
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established: {websocket.client}")
    
    try:
        # Get STT client
        stt = get_stt_client()
        
        # Create push audio stream for real-time audio
        audio_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=16000,
            bits_per_sample=16,
            channels=1
        )
        push_stream = speechsdk.audio.PushAudioInputStream(audio_format)
        audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
        
        # Track first token latency
        first_token_time = None
        session_start_time = time.time()
        
        # Define callbacks for streaming recognition
        def on_recognizing(evt):
            """Handle partial recognition results."""
            nonlocal first_token_time
            if first_token_time is None:
                first_token_time = time.time()
                latency = (first_token_time - session_start_time) * 1000
                logger.info(f"First token latency: {latency:.2f}ms")
            
            # Send partial result to client
            import asyncio
            asyncio.create_task(websocket.send_json({
                "type": "partial",
                "text": evt.result.text,
                "confidence": 0.8,  # Partial results have lower confidence
                "timestamp": time.time()
            }))
        
        def on_recognized(evt):
            """Handle final recognition results."""
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                # Send final result to client
                import asyncio
                asyncio.create_task(websocket.send_json({
                    "type": "final",
                    "text": evt.result.text,
                    "confidence": 1.0,
                    "timestamp": time.time()
                }))
        
        def on_canceled(evt):
            """Handle recognition errors."""
            logger.error(f"Recognition canceled: {evt.cancellation_details}")
            import asyncio
            asyncio.create_task(websocket.send_json({
                "type": "error",
                "message": str(evt.cancellation_details.error_details)
            }))
        
        # Start continuous recognition
        recognizer = await stt.transcribe_stream(
            audio_config=audio_config,
            callback_recognizing=on_recognizing,
            callback_recognized=on_recognized,
            callback_canceled=on_canceled
        )
        
        # Receive audio chunks from client
        try:
            while True:
                # Receive binary audio data
                data = await websocket.receive_bytes()
                
                # Push audio to recognizer
                push_stream.write(data)
                
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected by client")
        finally:
            # Stop recognition and close stream
            stt.stop_recognition(recognizer)
            push_stream.close()
            
            # Calculate session metrics
            session_duration = time.time() - session_start_time
            logger.info(
                f"Streaming session ended: duration={session_duration:.2f}s, "
                f"first_token_latency={first_token_time and (first_token_time - session_start_time) * 1000:.2f}ms"
            )
    
    except Exception as e:
        logger.error(f"Streaming transcription error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
        finally:
            await websocket.close()


@router.get("/languages")
async def get_supported_languages(stt: AzureSpeechSTT = Depends(get_stt_client)):
    """
    Get list of supported languages for speech recognition.
    
    Returns:
        List of language codes
    """
    return {
        "languages": stt.get_supported_languages(),
        "default": settings.azure_speech_language
    }


# ============================================================================
# TTS ENDPOINTS
# ============================================================================

@router.post("/synthesize", response_model=SynthesizeResponse)
async def synthesize_speech(
    request: SynthesizeRequest,
    tts: AzureSpeechTTS = Depends(get_tts_client)
):
    """
    Synthesize text to speech using Azure Neural TTS.
    
    This endpoint converts text to natural-sounding speech with:
    - Sub-100ms synthesis latency
    - Voice customization (pitch, rate, volume, style)
    - Multiple neural voices
    
    Args:
        request: Synthesis request with text and voice options
        
    Returns:
        SynthesizeResponse with synthesis metadata
        
    Note:
        To get the actual audio data, use the /synthesize/audio endpoint
    """
    try:
        # Build voice config
        voice_config = VoiceConfig(
            voice_name=request.voice_name or settings.azure_speech_voice,
            style=request.style or VoiceStyle.NEUTRAL,
            pitch=request.pitch or "+0%",
            rate=request.rate or "+0%",
            volume=request.volume or "+0%",
        )
        
        # Update TTS voice if different from default
        if request.voice_name and request.voice_name != tts.voice_name:
            tts.set_voice(request.voice_name)
        
        # Synthesize
        logger.info(f"Synthesizing text: length={len(request.text)}, voice={voice_config.voice_name}")
        result = await tts.synthesize(
            text=request.text,
            voice_config=voice_config,
            use_ssml=True
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=result.error_message or "Synthesis failed"
            )
        
        # Check latency target
        if result.latency > 100:
            logger.warning(
                f"Synthesis latency ({result.latency:.2f}ms) exceeded target (100ms)"
            )
        
        return SynthesizeResponse(
            success=result.success,
            duration=result.duration,
            latency=result.latency,
            voice_name=result.voice_name,
            audio_size=len(result.audio_data),
            error_message=result.error_message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Synthesis failed: {str(e)}"
        )


@router.post("/synthesize/audio")
async def synthesize_speech_audio(
    request: SynthesizeRequest,
    tts: AzureSpeechTTS = Depends(get_tts_client)
):
    """
    Synthesize text to speech and return audio data.
    
    This endpoint converts text to speech and returns the audio file directly.
    Optimized for <100ms synthesis latency.
    
    Args:
        request: Synthesis request with text and voice options
        
    Returns:
        Audio data (MP3 format) as binary response
        
    Raises:
        HTTPException: If synthesis fails
    """
    try:
        # Build voice config
        voice_config = VoiceConfig(
            voice_name=request.voice_name or settings.azure_speech_voice,
            style=request.style or VoiceStyle.NEUTRAL,
            pitch=request.pitch or "+0%",
            rate=request.rate or "+0%",
            volume=request.volume or "+0%",
        )
        
        # Update TTS voice if different from default
        if request.voice_name and request.voice_name != tts.voice_name:
            tts.set_voice(request.voice_name)
        
        # Synthesize
        logger.info(f"Synthesizing audio: length={len(request.text)}, voice={voice_config.voice_name}")
        result = await tts.synthesize(
            text=request.text,
            voice_config=voice_config,
            use_ssml=True
        )
        
        if not result.success:
            raise HTTPException(
                status_code=500,
                detail=result.error_message or "Synthesis failed"
            )
        
        logger.info(
            f"Synthesis complete: audio_size={len(result.audio_data)} bytes, "
            f"duration={result.duration:.2f}s, latency={result.latency:.2f}ms"
        )
        
        # Return audio data as MP3
        return Response(
            content=result.audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "X-Audio-Duration": str(result.duration),
                "X-Synthesis-Latency": str(result.latency),
                "X-Voice-Name": result.voice_name,
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Synthesis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Synthesis failed: {str(e)}"
        )


@router.get("/voices", response_model=VoicesResponse)
async def get_available_voices(
    language: Optional[str] = None,
    tts: AzureSpeechTTS = Depends(get_tts_client)
):
    """
    Get list of available neural voices.
    
    Args:
        language: Optional language filter (e.g., 'en-US', 'es-ES')
        
    Returns:
        List of available neural voice names
    """
    voices = tts.get_available_voices(language=language)
    
    return VoicesResponse(
        voices=voices,
        default_voice=settings.azure_speech_voice,
        language=language
    )



# ============================================================================
# VOICE PIPELINE SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    pipeline: VoicePipeline = Depends(get_pipeline)
):
    """
    Create a new voice session.
    
    This endpoint creates a new voice session with STT, TTS, and VAD components.
    The session manages turn-taking, interruption handling, and metrics tracking.
    
    Args:
        request: Session creation request with optional context
        
    Returns:
        SessionResponse with session details
    """
    try:
        session = await pipeline.start_session(context=request.context)
        
        return SessionResponse(
            session_id=session.session_id,
            state=session.state.value,
            turn_state=session.turn_state.value,
            created_at=session.created_at.isoformat(),
            metrics={
                "turn_count": session.metrics.turn_count,
                "user_turns": session.metrics.user_turns,
                "agent_turns": session.metrics.agent_turns,
                "interruptions": session.metrics.interruptions,
                "avg_latency": session.metrics.avg_latency,
            }
        )
    except Exception as e:
        logger.error(f"Failed to create session: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_info(
    session_id: str,
    pipeline: VoicePipeline = Depends(get_pipeline)
):
    """
    Get details of an active voice session.
    
    Args:
        session_id: Session ID
        
    Returns:
        SessionResponse with session details
        
    Raises:
        HTTPException: If session not found
    """
    session = pipeline.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return SessionResponse(
        session_id=session.session_id,
        state=session.state.value,
        turn_state=session.turn_state.value,
        created_at=session.created_at.isoformat(),
        metrics={
            "turn_count": session.metrics.turn_count,
            "user_turns": session.metrics.user_turns,
            "agent_turns": session.metrics.agent_turns,
            "interruptions": session.metrics.interruptions,
            "avg_latency": session.metrics.avg_latency,
        }
    )


@router.delete("/sessions/{session_id}")
async def end_session(
    session_id: str,
    pipeline: VoicePipeline = Depends(get_pipeline)
):
    """
    End an active voice session.
    
    Args:
        session_id: Session ID
        
    Returns:
        Success message with final metrics
    """
    session = pipeline.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    # Get final metrics before ending
    metrics = session.metrics
    
    await pipeline.end_session(session_id)
    
    return {
        "message": f"Session {session_id} ended successfully",
        "final_metrics": {
            "duration": metrics.get_session_duration(),
            "turn_count": metrics.turn_count,
            "user_turns": metrics.user_turns,
            "agent_turns": metrics.agent_turns,
            "interruptions": metrics.interruptions,
            "turn_taking_accuracy": metrics.get_turn_taking_accuracy(),
            "avg_latency": metrics.avg_latency,
        }
    }


@router.get("/sessions/{session_id}/metrics", response_model=SessionMetricsResponse)
async def get_session_metrics(
    session_id: str,
    pipeline: VoicePipeline = Depends(get_pipeline)
):
    """
    Get metrics for a voice session.
    
    Args:
        session_id: Session ID
        
    Returns:
        SessionMetricsResponse with detailed metrics
        
    Raises:
        HTTPException: If session not found
    """
    metrics = pipeline.get_session_metrics(session_id)
    
    if not metrics:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    return SessionMetricsResponse(
        session_id=metrics.session_id,
        duration=metrics.get_session_duration(),
        turn_count=metrics.turn_count,
        user_turns=metrics.user_turns,
        agent_turns=metrics.agent_turns,
        interruptions=metrics.interruptions,
        turn_taking_accuracy=metrics.get_turn_taking_accuracy(),
        avg_latency=metrics.avg_latency,
    )


@router.post("/sessions/{session_id}/interrupt")
async def interrupt_session(
    session_id: str,
    pipeline: VoicePipeline = Depends(get_pipeline)
):
    """
    Request interruption of agent speech in a session.
    
    This endpoint allows the user to interrupt the agent while it's speaking,
    implementing natural turn-taking behavior.
    
    Args:
        session_id: Session ID
        
    Returns:
        Success message indicating if interruption was handled
    """
    handled = pipeline.handle_interruption(session_id)
    
    if not handled:
        return {
            "message": f"Interruption not needed for session {session_id}",
            "handled": False
        }
    
    return {
        "message": f"Interruption handled for session {session_id}",
        "handled": True
    }


@router.post("/sessions/{session_id}/synthesize")
async def synthesize_for_session(
    session_id: str,
    request: SynthesizeRequest,
    pipeline: VoicePipeline = Depends(get_pipeline)
):
    """
    Synthesize speech within a session context.
    
    This endpoint synthesizes speech for a specific session, tracking metrics
    and managing turn-taking state.
    
    Args:
        session_id: Session ID
        request: Synthesis request
        
    Returns:
        Audio data (MP3 format) as binary response
    """
    try:
        # Build voice config
        voice_config = VoiceConfig(
            voice_name=request.voice_name or settings.azure_speech_voice,
            style=request.style or VoiceStyle.NEUTRAL,
            pitch=request.pitch or "+0%",
            rate=request.rate or "+0%",
            volume=request.volume or "+0%",
        )
        
        # Synthesize within session
        audio_data = await pipeline.synthesize_speech(
            session_id=session_id,
            text=request.text,
            voice_config=voice_config,
        )
        
        # Get session metrics
        session = pipeline.get_session(session_id)
        metrics = session.metrics if session else None
        
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "inline; filename=speech.mp3",
                "X-Session-ID": session_id,
                "X-Turn-Count": str(metrics.turn_count) if metrics else "0",
                "X-Avg-Latency": str(metrics.avg_latency) if metrics else "0",
            }
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Session synthesis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Session synthesis failed: {str(e)}"
        )
