"""
Example script to test Azure Speech Services STT integration
Run this script to verify Azure Speech configuration
"""

import asyncio
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from voice.stt import create_azure_stt
from core.config import settings


async def test_stt_configuration():
    """Test Azure Speech STT configuration."""
    print("=" * 60)
    print("Azure Speech Services STT Configuration Test")
    print("=" * 60)
    
    # Check configuration
    print("\n1. Checking configuration...")
    if not settings.use_azure_speech:
        print("❌ Azure Speech is not enabled")
        print("   Set USE_AZURE_SPEECH=true in .env file")
        return False
    
    if not settings.azure_speech_key:
        print("❌ Azure Speech key is not configured")
        print("   Set AZURE_SPEECH_KEY in .env file")
        return False
    
    if not settings.azure_speech_region:
        print("❌ Azure Speech region is not configured")
        print("   Set AZURE_SPEECH_REGION in .env file")
        return False
    
    print(f"✅ Azure Speech enabled: {settings.use_azure_speech}")
    print(f"✅ Region: {settings.azure_speech_region}")
    print(f"✅ Language: {settings.azure_speech_language}")
    print(f"✅ Voice: {settings.azure_speech_voice}")
    
    # Create STT client
    print("\n2. Creating STT client...")
    try:
        stt = create_azure_stt(
            subscription_key=settings.azure_speech_key,
            region=settings.azure_speech_region,
            language=settings.azure_speech_language
        )
        print("✅ STT client created successfully")
    except Exception as e:
        print(f"❌ Failed to create STT client: {e}")
        return False
    
    # Check supported languages
    print("\n3. Checking supported languages...")
    languages = stt.get_supported_languages()
    print(f"✅ Supported languages: {len(languages)}")
    print(f"   Sample: {', '.join(languages[:5])}")
    
    # Test language switching
    print("\n4. Testing language switching...")
    try:
        stt.set_language("es-ES")
        print("✅ Changed language to Spanish (es-ES)")
        stt.set_language(settings.azure_speech_language)
        print(f"✅ Changed language back to {settings.azure_speech_language}")
    except Exception as e:
        print(f"❌ Language switching failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All configuration tests passed!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Start the FastAPI server: uvicorn api.main:app --reload")
    print("2. Test the API endpoints:")
    print("   - GET  http://localhost:8000/api/v1/voice/health")
    print("   - POST http://localhost:8000/api/v1/voice/transcribe")
    print("   - WS   ws://localhost:8000/api/v1/voice/transcribe/stream")
    print("3. View API docs: http://localhost:8000/docs")
    
    return True


async def test_microphone_transcription():
    """Test real-time microphone transcription (interactive)."""
    print("\n" + "=" * 60)
    print("Interactive Microphone Transcription Test")
    print("=" * 60)
    print("\nThis test will use your default microphone.")
    print("Speak into your microphone and see the transcription in real-time.")
    print("Press Ctrl+C to stop.\n")
    
    try:
        # Create STT client
        stt = create_azure_stt(
            subscription_key=settings.azure_speech_key,
            region=settings.azure_speech_region,
            language=settings.azure_speech_language
        )
        
        # Define callbacks
        def on_recognizing(evt):
            """Handle partial results."""
            print(f"[Partial] {evt.result.text}")
        
        def on_recognized(evt):
            """Handle final results."""
            if evt.result.text:
                print(f"[Final]   {evt.result.text}")
        
        def on_canceled(evt):
            """Handle errors."""
            print(f"[Error]   {evt.cancellation_details}")
        
        # Start streaming recognition
        print("🎤 Listening... (speak now)")
        recognizer = await stt.transcribe_stream(
            callback_recognizing=on_recognizing,
            callback_recognized=on_recognized,
            callback_canceled=on_canceled
        )
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping recognition...")
            stt.stop_recognition(recognizer)
            print("✅ Recognition stopped")
    
    except Exception as e:
        print(f"❌ Microphone test failed: {e}")
        return False
    
    return True


async def main():
    """Main entry point."""
    print("\nTradeSense - Azure Speech Services STT Test\n")
    
    # Test configuration
    config_ok = await test_stt_configuration()
    
    if not config_ok:
        print("\n❌ Configuration test failed. Please fix the issues above.")
        return
    
    # Ask if user wants to test microphone
    print("\n" + "=" * 60)
    response = input("\nDo you want to test microphone transcription? (y/n): ")
    if response.lower() == 'y':
        await test_microphone_transcription()
    else:
        print("\nSkipping microphone test.")
    
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())
