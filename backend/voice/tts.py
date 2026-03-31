"""
Azure Speech Services Text-to-Speech (TTS) Integration
Implements neural voice synthesis with <100ms latency
Optimized for natural-sounding field service interactions
"""

import logging
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum
import azure.cognitiveservices.speech as speechsdk
from azure.cognitiveservices.speech import (
    SpeechConfig,
    AudioConfig,
    SpeechSynthesizer,
    ResultReason,
    CancellationReason,
    SpeechSynthesisOutputFormat,
)

logger = logging.getLogger(__name__)


class VoiceStyle(str, Enum):
    """Available voice styles for Azure Neural TTS."""
    NEUTRAL = "neutral"
    CHEERFUL = "cheerful"
    EMPATHETIC = "empathetic"
    CALM = "calm"
    ASSISTANT = "assistant"
    NEWSCAST = "newscast"
    CUSTOMER_SERVICE = "customerservice"


@dataclass
class VoiceConfig:
    """Voice customization configuration."""
    voice_name: str = "en-US-JennyNeural"
    style: VoiceStyle = VoiceStyle.NEUTRAL
    pitch: str = "+0%"  # Range: -50% to +50%
    rate: str = "+0%"   # Range: -50% to +200%
    volume: str = "+0%"  # Range: -50% to +50%


@dataclass
class SynthesisResult:
    """TTS synthesis result."""
    audio_data: bytes
    duration: float
    latency: float
    voice_name: str
    success: bool
    error_message: Optional[str] = None


class AzureSpeechTTS:
    """
    Azure Speech Services TTS client with neural voice support.
    
    Features:
    - Neural voice synthesis with <100ms latency
    - Voice customization (pitch, rate, volume, style)
    - Multiple neural voices (Jenny, Guy, Aria, Davis, etc.)
    - SSML support for advanced control
    - Streaming synthesis for long text
    """

    # Popular Azure Neural Voices
    NEURAL_VOICES = {
        "en-US": [
            "en-US-JennyNeural",      # Female, general purpose
            "en-US-GuyNeural",        # Male, general purpose
            "en-US-AriaNeural",       # Female, customer service
            "en-US-DavisNeural",      # Male, professional
            "en-US-AmberNeural",      # Female, young adult
            "en-US-AshleyNeural",     # Female, young adult
            "en-US-BrandonNeural",    # Male, young adult
            "en-US-ChristopherNeural", # Male, mature
            "en-US-CoraNeural",       # Female, mature
            "en-US-ElizabethNeural",  # Female, mature
            "en-US-EricNeural",       # Male, mature
            "en-US-JacobNeural",      # Male, young adult
            "en-US-JaneNeural",       # Female, young adult
            "en-US-JasonNeural",      # Male, professional
            "en-US-MichelleNeural",   # Female, professional
            "en-US-MonicaNeural",     # Female, professional
            "en-US-NancyNeural",      # Female, professional
            "en-US-RogerNeural",      # Male, mature
            "en-US-SaraNeural",       # Female, professional
            "en-US-SteffanNeural",    # Male, professional
            "en-US-TonyNeural",       # Male, professional
        ],
        "en-GB": [
            "en-GB-SoniaNeural",
            "en-GB-RyanNeural",
            "en-GB-LibbyNeural",
        ],
        "es-ES": [
            "es-ES-ElviraNeural",
            "es-ES-AlvaroNeural",
        ],
        "fr-FR": [
            "fr-FR-DeniseNeural",
            "fr-FR-HenriNeural",
        ],
        "de-DE": [
            "de-DE-KatjaNeural",
            "de-DE-ConradNeural",
        ],
    }

    def __init__(
        self,
        subscription_key: str,
        region: str,
        voice_name: str = "en-US-JennyNeural",
        output_format: SpeechSynthesisOutputFormat = SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3,
    ):
        """
        Initialize Azure Speech TTS client.
        
        Args:
            subscription_key: Azure Speech Services API key
            region: Azure region (e.g., 'eastus', 'westus')
            voice_name: Neural voice name (default: en-US-JennyNeural)
            output_format: Audio output format
        """
        self.subscription_key = subscription_key
        self.region = region
        self.voice_name = voice_name
        
        # Create speech config
        self.speech_config = SpeechConfig(
            subscription=subscription_key,
            region=region
        )
        
        # Set voice
        self.speech_config.speech_synthesis_voice_name = voice_name
        
        # Set output format for optimal quality and size
        self.speech_config.set_speech_synthesis_output_format(output_format)
        
        # Optimize for low latency
        # Enable streaming for faster first-byte response
        self.speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_SynthEnableCompressedAudioTransmission,
            "true"
        )
        
        logger.info(
            f"Initialized Azure Speech TTS client: region={region}, "
            f"voice={voice_name}, format={output_format}"
        )

    def create_synthesizer(
        self,
        audio_config: Optional[AudioConfig] = None
    ) -> SpeechSynthesizer:
        """
        Create a speech synthesizer instance.
        
        Args:
            audio_config: Audio configuration (default: return audio data)
            
        Returns:
            Configured SpeechSynthesizer instance
        """
        if audio_config is None:
            # Use None to return audio data instead of playing to speaker
            audio_config = None
        
        synthesizer = SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        return synthesizer

    async def synthesize(
        self,
        text: str,
        voice_config: Optional[VoiceConfig] = None,
        use_ssml: bool = False
    ) -> SynthesisResult:
        """
        Synthesize text to speech.
        
        Args:
            text: Text to synthesize
            voice_config: Voice customization options
            use_ssml: Whether to use SSML for advanced control
            
        Returns:
            SynthesisResult with audio data and metadata
            
        Raises:
            RuntimeError: If synthesis fails
        """
        import time
        start_time = time.time()
        
        synthesizer = self.create_synthesizer()
        
        try:
            # Build SSML if customization requested
            if voice_config or use_ssml:
                ssml = self._build_ssml(text, voice_config or VoiceConfig())
                logger.debug(f"Using SSML: {ssml}")
                result = synthesizer.speak_ssml_async(ssml).get()
            else:
                result = synthesizer.speak_text_async(text).get()
            
            latency = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            if result.reason == ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                duration = result.audio_duration.total_seconds()
                
                logger.info(
                    f"Synthesis complete: text_length={len(text)}, "
                    f"audio_duration={duration:.2f}s, latency={latency:.2f}ms"
                )
                
                # Check latency target
                if latency > 100:
                    logger.warning(
                        f"Synthesis latency ({latency:.2f}ms) exceeded target (100ms)"
                    )
                
                return SynthesisResult(
                    audio_data=audio_data,
                    duration=duration,
                    latency=latency,
                    voice_name=self.voice_name,
                    success=True
                )
            
            elif result.reason == ResultReason.Canceled:
                cancellation = result.cancellation_details
                error_msg = f"Synthesis canceled: {cancellation.reason}"
                
                if cancellation.reason == CancellationReason.Error:
                    error_msg += f" - {cancellation.error_details}"
                    logger.error(error_msg)
                
                return SynthesisResult(
                    audio_data=b"",
                    duration=0.0,
                    latency=latency,
                    voice_name=self.voice_name,
                    success=False,
                    error_message=error_msg
                )
            
            else:
                error_msg = f"Unexpected result reason: {result.reason}"
                logger.error(error_msg)
                return SynthesisResult(
                    audio_data=b"",
                    duration=0.0,
                    latency=latency,
                    voice_name=self.voice_name,
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            error_msg = f"Synthesis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return SynthesisResult(
                audio_data=b"",
                duration=0.0,
                latency=latency,
                voice_name=self.voice_name,
                success=False,
                error_message=error_msg
            )

    def _build_ssml(self, text: str, voice_config: VoiceConfig) -> str:
        """
        Build SSML markup for voice customization.
        
        Args:
            text: Text to synthesize
            voice_config: Voice customization options
            
        Returns:
            SSML string
        """
        # Escape XML special characters in text
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Build SSML with voice customization
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" 
               xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="en-US">
            <voice name="{voice_config.voice_name}">
                <mstts:express-as style="{voice_config.style.value}">
                    <prosody pitch="{voice_config.pitch}" rate="{voice_config.rate}" volume="{voice_config.volume}">
                        {text}
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """
        
        return ssml.strip()

    async def synthesize_streaming(
        self,
        text: str,
        voice_config: Optional[VoiceConfig] = None,
        callback_audio_chunk: Optional[callable] = None,
    ) -> SynthesisResult:
        """
        Synthesize text to speech with streaming output.
        
        This method provides audio chunks as they're generated for lower latency.
        
        Args:
            text: Text to synthesize
            voice_config: Voice customization options
            callback_audio_chunk: Called for each audio chunk
            
        Returns:
            SynthesisResult with complete audio data
            
        Example:
            def on_audio_chunk(chunk):
                print(f"Received {len(chunk)} bytes")
            
            result = await tts.synthesize_streaming(
                "Hello world",
                callback_audio_chunk=on_audio_chunk
            )
        """
        import time
        start_time = time.time()
        
        # Create pull audio output stream for streaming
        stream_callback = speechsdk.audio.PullAudioOutputStream()
        audio_config = AudioConfig(stream=stream_callback)
        
        synthesizer = SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        # Track audio chunks
        audio_chunks = []
        
        # Set up event handlers for streaming
        def on_synthesizing(evt):
            """Handle audio chunks as they're generated."""
            if evt.result.audio_data:
                audio_chunks.append(evt.result.audio_data)
                if callback_audio_chunk:
                    callback_audio_chunk(evt.result.audio_data)
        
        synthesizer.synthesizing.connect(on_synthesizing)
        
        try:
            # Build SSML if customization requested
            if voice_config:
                ssml = self._build_ssml(text, voice_config)
                result = synthesizer.speak_ssml_async(ssml).get()
            else:
                result = synthesizer.speak_text_async(text).get()
            
            latency = (time.time() - start_time) * 1000
            
            if result.reason == ResultReason.SynthesizingAudioCompleted:
                # Combine all chunks
                audio_data = b"".join(audio_chunks) if audio_chunks else result.audio_data
                duration = result.audio_duration.total_seconds()
                
                logger.info(
                    f"Streaming synthesis complete: chunks={len(audio_chunks)}, "
                    f"duration={duration:.2f}s, latency={latency:.2f}ms"
                )
                
                return SynthesisResult(
                    audio_data=audio_data,
                    duration=duration,
                    latency=latency,
                    voice_name=self.voice_name,
                    success=True
                )
            
            else:
                error_msg = f"Streaming synthesis failed: {result.reason}"
                logger.error(error_msg)
                return SynthesisResult(
                    audio_data=b"",
                    duration=0.0,
                    latency=latency,
                    voice_name=self.voice_name,
                    success=False,
                    error_message=error_msg
                )
                
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            error_msg = f"Streaming synthesis failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return SynthesisResult(
                audio_data=b"",
                duration=0.0,
                latency=latency,
                voice_name=self.voice_name,
                success=False,
                error_message=error_msg
            )

    def get_available_voices(self, language: Optional[str] = None) -> List[str]:
        """
        Get list of available neural voices.
        
        Args:
            language: Filter by language code (e.g., 'en-US')
            
        Returns:
            List of voice names
        """
        if language:
            return self.NEURAL_VOICES.get(language, [])
        
        # Return all voices
        all_voices = []
        for voices in self.NEURAL_VOICES.values():
            all_voices.extend(voices)
        return all_voices

    def set_voice(self, voice_name: str) -> None:
        """
        Change the synthesis voice.
        
        Args:
            voice_name: Neural voice name (e.g., 'en-US-JennyNeural')
        """
        self.voice_name = voice_name
        self.speech_config.speech_synthesis_voice_name = voice_name
        logger.info(f"Changed synthesis voice to: {voice_name}")

    @staticmethod
    def create_audio_config_to_file(filename: str) -> AudioConfig:
        """
        Create audio configuration to save to file.
        
        Args:
            filename: Output file path (WAV format)
            
        Returns:
            AudioConfig instance
        """
        return AudioConfig(filename=filename)


# Factory function for easy instantiation
def create_azure_tts(
    subscription_key: str,
    region: str,
    voice_name: str = "en-US-JennyNeural",
    **kwargs
) -> AzureSpeechTTS:
    """
    Factory function to create Azure Speech TTS client.
    
    Args:
        subscription_key: Azure Speech Services API key
        region: Azure region
        voice_name: Neural voice name
        **kwargs: Additional configuration options
        
    Returns:
        Configured AzureSpeechTTS instance
    """
    return AzureSpeechTTS(
        subscription_key=subscription_key,
        region=region,
        voice_name=voice_name,
        **kwargs
    )
