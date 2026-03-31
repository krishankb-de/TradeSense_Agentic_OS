"""
Example: Voice Pipeline Orchestrator Usage
Demonstrates session management, turn-taking, and interruption handling
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from voice.pipeline import create_voice_pipeline, VoiceConfig, VoiceStyle
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def main():
    """Demonstrate voice pipeline usage."""
    
    # Get Azure credentials
    azure_key = os.getenv("AZURE_SPEECH_KEY")
    azure_region = os.getenv("AZURE_SPEECH_REGION", "eastus")
    
    if not azure_key:
        print("Error: AZURE_SPEECH_KEY not set in .env file")
        return
    
    print("=" * 60)
    print("Voice Pipeline Orchestrator Demo")
    print("=" * 60)
    
    # Create pipeline
    print("\n1. Creating voice pipeline...")
    pipeline = create_voice_pipeline(
        azure_speech_key=azure_key,
        azure_speech_region=azure_region,
        stt_language="en-US",
        tts_voice_name="en-US-JennyNeural",
        latency_target_ms=500,
    )
    
    await pipeline.initialize()
    print("   ✓ Pipeline initialized")
    
    # Start a session
    print("\n2. Starting voice session...")
    session = await pipeline.start_session(
        context={"user_id": "demo-user", "test": True}
    )
    print(f"   ✓ Session created: {session.session_id}")
    print(f"   - State: {session.state.value}")
    print(f"   - Turn state: {session.turn_state.value}")
    
    # Set up callbacks
    print("\n3. Setting up callbacks...")
    
    def on_transcription(session_id, text, is_final):
        status = "FINAL" if is_final else "PARTIAL"
        print(f"   [{status}] Transcription: {text}")
    
    def on_speech_start(session_id, timestamp):
        print(f"   🎤 Speech started at {timestamp:.2f}s")
    
    def on_speech_end(session_id, timestamp):
        print(f"   🔇 Speech ended at {timestamp:.2f}s")
    
    def on_interruption(session_id):
        print(f"   ⚠️  Interruption detected!")
    
    pipeline.set_callbacks(
        on_transcription=on_transcription,
        on_speech_start=on_speech_start,
        on_speech_end=on_speech_end,
        on_interruption=on_interruption,
    )
    print("   ✓ Callbacks configured")
    
    # Synthesize speech
    print("\n4. Synthesizing speech...")
    text = "Hello! This is a test of the voice pipeline orchestrator."
    
    voice_config = VoiceConfig(
        voice_name="en-US-JennyNeural",
        style=VoiceStyle.CHEERFUL,
        rate="+0%",
    )
    
    audio_data = await pipeline.synthesize_speech(
        session_id=session.session_id,
        text=text,
        voice_config=voice_config,
    )
    
    print(f"   ✓ Synthesized {len(audio_data)} bytes of audio")
    print(f"   - Session state: {session.state.value}")
    print(f"   - Turn state: {session.turn_state.value}")
    
    # Simulate some activity
    print("\n5. Simulating session activity...")
    session.metrics.user_turns = 3
    session.metrics.agent_turns = 3
    session.metrics.turn_count = 6
    session.metrics.add_latency(450.0)
    session.metrics.add_latency(480.0)
    session.metrics.add_latency(520.0)
    print("   ✓ Activity simulated")
    
    # Test interruption handling
    print("\n6. Testing interruption handling...")
    session.state = "speaking"  # Simulate agent speaking
    handled = pipeline.handle_interruption(session.session_id)
    print(f"   ✓ Interruption handled: {handled}")
    print(f"   - Interruptions count: {session.metrics.interruptions}")
    
    # Get session metrics
    print("\n7. Session metrics:")
    metrics = pipeline.get_session_metrics(session.session_id)
    if metrics:
        print(f"   - Duration: {metrics.get_session_duration():.2f}s")
        print(f"   - Total turns: {metrics.turn_count}")
        print(f"   - User turns: {metrics.user_turns}")
        print(f"   - Agent turns: {metrics.agent_turns}")
        print(f"   - Interruptions: {metrics.interruptions}")
        print(f"   - Turn-taking accuracy: {metrics.get_turn_taking_accuracy():.1%}")
        print(f"   - Average latency: {metrics.avg_latency:.2f}ms")
    
    # End session
    print("\n8. Ending session...")
    await pipeline.end_session(session.session_id)
    print(f"   ✓ Session ended")
    
    # Verify session is removed
    remaining = pipeline.get_session(session.session_id)
    print(f"   - Session in active sessions: {remaining is not None}")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
