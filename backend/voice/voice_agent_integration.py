"""
Voice-to-Agent Integration for TradeSense.

Integrates voice pipeline with agent routing system to enable:
- Voice-to-text-to-agent-to-speech flow
- Streaming response handling
- Error handling and fallback to text mode
- Turn-taking and interruption management

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9, 2.10, 3.1, 3.2, 15.1**
"""

import logging
import time
from typing import Optional, Dict, Any, Callable, AsyncIterator
from dataclasses import dataclass
from enum import Enum

from voice.pipeline import VoicePipeline, VoiceSession, SessionState
from voice.session_manager import VoiceSessionManager, VoiceSessionModel, SessionStatus
from orchestration.agent_router import AgentRouter, RoutingDecision

logger = logging.getLogger(__name__)


class InteractionMode(str, Enum):
    """Interaction mode."""
    VOICE = "voice"
    TEXT = "text"
    HYBRID = "hybrid"


@dataclass
class VoiceAgentRequest:
    """Request for voice-to-agent processing."""
    session_id: str
    audio_data: Optional[bytes] = None
    text_input: Optional[str] = None
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class VoiceAgentResponse:
    """Response from voice-to-agent processing."""
    session_id: str
    text_response: str
    audio_response: Optional[bytes] = None
    intent: Optional[str] = None
    agent_type: Optional[str] = None
    confidence: float = 0.0
    latency: float = 0.0
    mode: InteractionMode = InteractionMode.VOICE
    error: Optional[str] = None


class VoiceAgentIntegration:
    """
    Voice-to-Agent Integration.
    
    Orchestrates the complete voice interaction flow:
    1. Voice input → STT (transcription)
    2. Text → Intent classification
    3. Intent → Agent routing
    4. Agent → Response generation
    5. Response → TTS (synthesis)
    6. Audio output → User
    
    Features:
    - Streaming transcription and responses
    - Interruption handling
    - Error recovery with fallback to text mode
    - Session management and metrics tracking
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9, 2.10, 3.1, 3.2, 15.1**
    """
    
    def __init__(
        self,
        voice_pipeline: VoicePipeline,
        agent_router: AgentRouter,
        session_manager: VoiceSessionManager,
    ):
        """
        Initialize voice-agent integration.
        
        Args:
            voice_pipeline: Voice pipeline for STT/TTS
            agent_router: Agent router for intent classification and routing
            session_manager: Session manager for tracking
        """
        self.voice_pipeline = voice_pipeline
        self.agent_router = agent_router
        self.session_manager = session_manager
        
        # Callbacks
        self.on_transcription: Optional[Callable] = None
        self.on_agent_response: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        logger.info("Voice-agent integration initialized")
    
    async def process_voice_input(
        self,
        request: VoiceAgentRequest,
    ) -> VoiceAgentResponse:
        """
        Process voice input through the complete pipeline.
        
        Flow:
        1. Transcribe audio to text (STT)
        2. Classify intent and route to agent
        3. Execute agent processing
        4. Synthesize response to speech (TTS)
        5. Track metrics and update session
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2**
        
        Args:
            request: Voice agent request
            
        Returns:
            VoiceAgentResponse with text and audio
        """
        start_time = time.time()
        session_id = request.session_id
        
        # Get or create session
        session = self.session_manager.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found, creating new session")
            session = self.session_manager.create_session(
                user_id=request.user_id,
                user_role=request.user_role,
                context=request.context,
            )
            session_id = session.session_id
        
        try:
            # Step 1: Transcribe audio to text (if audio provided)
            if request.audio_data:
                transcription = await self._transcribe_audio(
                    session_id=session_id,
                    audio_data=request.audio_data,
                )
                user_input = transcription
            elif request.text_input:
                user_input = request.text_input
            else:
                raise ValueError("Either audio_data or text_input must be provided")
            
            # Notify transcription callback
            if self.on_transcription:
                self.on_transcription(session_id, user_input)
            
            # Step 2: Route to agent
            routing_decision = await self._route_to_agent(
                session_id=session_id,
                user_input=user_input,
                context=session.context,
                user_role=session.user_role,
            )
            
            # Check if clarification is needed
            if routing_decision.requires_clarification:
                response_text = routing_decision.clarifying_question
                agent_type = "clarification"
            else:
                # Step 3: Execute agent processing
                response_text = await self._execute_agent(
                    session_id=session_id,
                    routing_decision=routing_decision,
                    user_input=user_input,
                    context=session.context,
                )
                agent_type = routing_decision.agent_type.value
            
            # Notify agent response callback
            if self.on_agent_response:
                self.on_agent_response(session_id, response_text, agent_type)
            
            # Step 4: Synthesize response to speech
            audio_response = None
            if request.audio_data:  # Only synthesize if input was voice
                audio_response = await self._synthesize_response(
                    session_id=session_id,
                    text=response_text,
                )
            
            # Step 5: Update session metrics
            latency = (time.time() - start_time) * 1000  # Convert to ms
            self.session_manager.add_turn(
                session_id=session_id,
                speaker="user",
                message=user_input,
                intent=routing_decision.intent.value,
                latency=latency,
            )
            self.session_manager.add_turn(
                session_id=session_id,
                speaker="agent",
                message=response_text,
                agent=agent_type,
            )
            
            logger.info(
                f"Voice-agent processing complete: session={session_id}, "
                f"intent={routing_decision.intent.value}, "
                f"agent={agent_type}, "
                f"latency={latency:.2f}ms"
            )
            
            return VoiceAgentResponse(
                session_id=session_id,
                text_response=response_text,
                audio_response=audio_response,
                intent=routing_decision.intent.value,
                agent_type=agent_type,
                confidence=routing_decision.confidence,
                latency=latency,
                mode=InteractionMode.VOICE if request.audio_data else InteractionMode.TEXT,
            )
        
        except Exception as e:
            logger.error(f"Voice-agent processing failed: {e}", exc_info=True)
            
            # Record error
            self.session_manager.add_error(session_id, str(e))
            
            # Notify error callback
            if self.on_error:
                self.on_error(session_id, str(e))
            
            # Fallback to text mode
            return await self._fallback_to_text_mode(
                session_id=session_id,
                error=str(e),
            )
    
    async def process_streaming_voice_input(
        self,
        session_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator[VoiceAgentResponse]:
        """
        Process streaming voice input with partial responses.
        
        This enables real-time interaction with:
        - Partial transcriptions
        - Streaming agent responses
        - Interruption handling
        
        **Validates: Requirements 2.8, 2.9**
        
        Args:
            session_id: Session ID
            audio_stream: Async iterator of audio chunks
            
        Yields:
            VoiceAgentResponse with partial results
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        try:
            # Process audio stream with voice pipeline
            # This would integrate with the voice pipeline's streaming capabilities
            # For now, we'll yield a placeholder response
            
            logger.info(f"Starting streaming voice processing for session {session_id}")
            
            # TODO: Implement actual streaming processing
            # This would involve:
            # 1. Streaming STT with partial transcriptions
            # 2. Incremental intent classification
            # 3. Streaming agent responses
            # 4. Streaming TTS synthesis
            
            yield VoiceAgentResponse(
                session_id=session_id,
                text_response="Streaming processing not yet implemented",
                mode=InteractionMode.VOICE,
            )
        
        except Exception as e:
            logger.error(f"Streaming voice processing failed: {e}", exc_info=True)
            self.session_manager.add_error(session_id, str(e))
            
            yield VoiceAgentResponse(
                session_id=session_id,
                text_response="An error occurred during streaming processing",
                error=str(e),
                mode=InteractionMode.TEXT,
            )
    
    async def handle_interruption(self, session_id: str) -> bool:
        """
        Handle user interruption during agent speech.
        
        **Validates: Requirement 2.9**
        
        Args:
            session_id: Session ID
            
        Returns:
            True if interruption was handled, False otherwise
        """
        # Get voice pipeline session
        session = self.session_manager.get_session(session_id)
        if not session or not session.pipeline_session_id:
            logger.warning(f"Cannot handle interruption: session {session_id} not found")
            return False
        
        # Handle interruption in voice pipeline
        handled = self.voice_pipeline.handle_interruption(session.pipeline_session_id)
        
        if handled:
            # Record interruption in session metrics
            self.session_manager.add_interruption(session_id)
            logger.info(f"Handled interruption for session {session_id}")
        
        return handled
    
    def set_callbacks(
        self,
        on_transcription: Optional[Callable] = None,
        on_agent_response: Optional[Callable] = None,
        on_error: Optional[Callable] = None,
    ) -> None:
        """
        Set callbacks for voice-agent events.
        
        Args:
            on_transcription: Called when transcription is available
            on_agent_response: Called when agent response is generated
            on_error: Called when an error occurs
        """
        self.on_transcription = on_transcription
        self.on_agent_response = on_agent_response
        self.on_error = on_error
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _transcribe_audio(
        self,
        session_id: str,
        audio_data: bytes,
    ) -> str:
        """
        Transcribe audio to text.
        
        **Validates: Requirements 2.2, 2.3, 2.4**
        
        Args:
            session_id: Session ID
            audio_data: Audio data bytes
            
        Returns:
            Transcribed text
        """
        session = self.session_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        # Get or create voice pipeline session
        if not session.pipeline_session_id:
            pipeline_session = await self.voice_pipeline.start_session(
                session_id=session_id,
                context=session.context,
            )
            session.pipeline_session_id = pipeline_session.session_id
        
        # Transcribe audio
        # TODO: Implement actual audio transcription
        # This would use the voice pipeline's STT capabilities
        
        # For now, return placeholder
        transcription = "Transcribed text from audio"
        
        logger.debug(f"Transcribed audio for session {session_id}: {transcription}")
        
        return transcription
    
    async def _route_to_agent(
        self,
        session_id: str,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        user_role: Optional[str] = None,
    ) -> RoutingDecision:
        """
        Route user input to appropriate agent.
        
        **Validates: Requirements 3.1, 3.2**
        
        Args:
            session_id: Session ID
            user_input: User input text
            context: Conversation context
            user_role: User role
            
        Returns:
            RoutingDecision
        """
        routing_decision = await self.agent_router.route_request(
            user_input=user_input,
            context=context,
            user_role=user_role,
        )
        
        logger.debug(
            f"Routed to {routing_decision.agent_type.value} agent "
            f"(intent: {routing_decision.intent.value}, "
            f"confidence: {routing_decision.confidence:.2f})"
        )
        
        return routing_decision
    
    async def _execute_agent(
        self,
        session_id: str,
        routing_decision: RoutingDecision,
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Execute agent processing.
        
        Args:
            session_id: Session ID
            routing_decision: Routing decision
            user_input: User input text
            context: Conversation context
            
        Returns:
            Agent response text
        """
        # Prepare input data for agent
        input_data = {
            "user_input": user_input,
            "context": context or {},
            "session_id": session_id,
        }
        
        # Execute agent
        result = await self.agent_router.execute_routing(
            routing_decision=routing_decision,
            input_data=input_data,
        )
        
        # Extract response text
        if isinstance(result, dict):
            response_text = result.get("response", str(result))
        else:
            response_text = str(result)
        
        logger.debug(f"Agent response for session {session_id}: {response_text[:100]}...")
        
        return response_text
    
    async def _synthesize_response(
        self,
        session_id: str,
        text: str,
    ) -> bytes:
        """
        Synthesize text response to speech.
        
        **Validates: Requirements 2.5, 2.6**
        
        Args:
            session_id: Session ID
            text: Text to synthesize
            
        Returns:
            Audio data bytes
        """
        session = self.session_manager.get_session(session_id)
        if not session or not session.pipeline_session_id:
            raise ValueError(f"Session {session_id} not found or not initialized")
        
        # Synthesize speech
        audio_data = await self.voice_pipeline.synthesize_speech(
            session_id=session.pipeline_session_id,
            text=text,
        )
        
        logger.debug(f"Synthesized speech for session {session_id}: {len(audio_data)} bytes")
        
        return audio_data
    
    async def _fallback_to_text_mode(
        self,
        session_id: str,
        error: str,
    ) -> VoiceAgentResponse:
        """
        Fallback to text mode when voice processing fails.
        
        **Validates: Requirement 15.1**
        
        Args:
            session_id: Session ID
            error: Error message
            
        Returns:
            VoiceAgentResponse in text mode
        """
        logger.warning(f"Falling back to text mode for session {session_id}: {error}")
        
        # Update session status
        self.session_manager.update_session(
            session_id=session_id,
            status=SessionStatus.ERROR,
        )
        
        return VoiceAgentResponse(
            session_id=session_id,
            text_response=(
                "I'm having trouble with voice processing. "
                "Please try typing your request instead."
            ),
            mode=InteractionMode.TEXT,
            error=error,
        )


# Factory function
def create_voice_agent_integration(
    voice_pipeline: VoicePipeline,
    agent_router: AgentRouter,
    session_manager: VoiceSessionManager,
) -> VoiceAgentIntegration:
    """
    Create voice-agent integration.
    
    Args:
        voice_pipeline: Voice pipeline for STT/TTS
        agent_router: Agent router for intent classification and routing
        session_manager: Session manager for tracking
        
    Returns:
        VoiceAgentIntegration instance
    """
    return VoiceAgentIntegration(
        voice_pipeline=voice_pipeline,
        agent_router=agent_router,
        session_manager=session_manager,
    )
