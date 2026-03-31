"""
Example script to test Azure Speech Services TTS
Demonstrates voice synthesis with customization options
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from voice.tts import create_azure_tts, VoiceConfig, VoiceStyle
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_basic_synthesis():
    """Test basic text-to-speech synthesis."""
    print("\n=== Testing Basic TTS Synthesis ===")
    
    # Get credentials from environment
    subscription_key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION", "eastus")
    
    if not subscription_key:
        print("ERROR: AZURE_SPEECH_KEY not set in .env file")
        return
    
    # Create TTS client
    print(f"Creating TTS client (region: {region})...")
    tts = create_azure_tts(
        subscription_key=subscription_key,
        region=region,
        voice_name="en-US-JennyNeural"
    )
    
    # Test synthesis
    text = "Hello! This is a test of Azure Speech Services text-to-speech."
    print(f"\nSynthesizing: '{text}'")
    
    result = await tts.synthesize(text)
    
    if result.success:
        print(f"✓ Synthesis successful!")
        print(f"  - Duration: {result.duration:.2f} seconds")
        print(f"  - Latency: {result.latency:.2f} ms")
        print(f"  - Audio size: {len(result.audio_data)} bytes")
        print(f"  - Voice: {result.voice_name}")
        
        # Check latency requirement
        if result.latency < 100:
            print(f"  ✓ Latency meets <100ms requirement")
        else:
            print(f"  ⚠ Latency exceeds 100ms target (actual: {result.latency:.2f}ms)")
        
        # Save audio to file
        output_file = "test_output_basic.mp3"
        with open(output_file, "wb") as f:
            f.write(result.audio_data)
        print(f"\n✓ Audio saved to: {output_file}")
    else:
        print(f"✗ Synthesis failed: {result.error_message}")


async def test_voice_customization():
    """Test voice customization with different styles."""
    print("\n=== Testing Voice Customization ===")
    
    subscription_key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION", "eastus")
    
    if not subscription_key:
        print("ERROR: AZURE_SPEECH_KEY not set in .env file")
        return
    
    tts = create_azure_tts(
        subscription_key=subscription_key,
        region=region,
        voice_name="en-US-AriaNeural"
    )
    
    # Test different voice styles
    test_cases = [
        {
            "text": "Welcome to TradeSense! How can I help you today?",
            "config": VoiceConfig(
                voice_name="en-US-AriaNeural",
                style=VoiceStyle.CHEERFUL,
                pitch="+0%",
                rate="+0%",
                volume="+0%"
            ),
            "filename": "test_output_cheerful.mp3"
        },
        {
            "text": "I understand this is urgent. Let me help you right away.",
            "config": VoiceConfig(
                voice_name="en-US-AriaNeural",
                style=VoiceStyle.EMPATHETIC,
                pitch="-5%",
                rate="-10%",
                volume="+0%"
            ),
            "filename": "test_output_empathetic.mp3"
        },
        {
            "text": "Your technician will arrive in 30 minutes. Please stay calm.",
            "config": VoiceConfig(
                voice_name="en-US-AriaNeural",
                style=VoiceStyle.CALM,
                pitch="-10%",
                rate="-5%",
                volume="+0%"
            ),
            "filename": "test_output_calm.mp3"
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['config'].style.value} style")
        print(f"Text: '{test_case['text']}'")
        
        result = await tts.synthesize(
            text=test_case["text"],
            voice_config=test_case["config"],
            use_ssml=True
        )
        
        if result.success:
            print(f"  ✓ Success - Latency: {result.latency:.2f}ms, Duration: {result.duration:.2f}s")
            
            # Save audio
            with open(test_case["filename"], "wb") as f:
                f.write(result.audio_data)
            print(f"  ✓ Saved to: {test_case['filename']}")
        else:
            print(f"  ✗ Failed: {result.error_message}")


async def test_multiple_voices():
    """Test different neural voices."""
    print("\n=== Testing Multiple Neural Voices ===")
    
    subscription_key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION", "eastus")
    
    if not subscription_key:
        print("ERROR: AZURE_SPEECH_KEY not set in .env file")
        return
    
    tts = create_azure_tts(
        subscription_key=subscription_key,
        region=region
    )
    
    # Test different voices
    voices = [
        ("en-US-JennyNeural", "Female, general purpose"),
        ("en-US-GuyNeural", "Male, general purpose"),
        ("en-US-AriaNeural", "Female, customer service"),
        ("en-US-DavisNeural", "Male, professional"),
    ]
    
    text = "Job logged successfully. Total cost is two hundred eighty-five dollars."
    
    for voice_name, description in voices:
        print(f"\nTesting: {voice_name} ({description})")
        
        tts.set_voice(voice_name)
        result = await tts.synthesize(text)
        
        if result.success:
            print(f"  ✓ Success - Latency: {result.latency:.2f}ms")
            
            # Save audio
            filename = f"test_output_{voice_name.replace('-', '_').lower()}.mp3"
            with open(filename, "wb") as f:
                f.write(result.audio_data)
            print(f"  ✓ Saved to: {filename}")
        else:
            print(f"  ✗ Failed: {result.error_message}")


async def test_latency_benchmark():
    """Benchmark synthesis latency with different text lengths."""
    print("\n=== Latency Benchmark ===")
    
    subscription_key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION", "eastus")
    
    if not subscription_key:
        print("ERROR: AZURE_SPEECH_KEY not set in .env file")
        return
    
    tts = create_azure_tts(
        subscription_key=subscription_key,
        region=region,
        voice_name="en-US-JennyNeural"
    )
    
    test_texts = [
        ("Short", "Hello."),
        ("Medium", "Your appointment is confirmed for 2 PM today."),
        ("Long", "Job logged successfully. I replaced the water heater thermostat model WH-500 and installed a new pressure relief valve PRV-200. The total cost is two hundred eighty-five dollars. Carbon footprint is 2.3 kilograms of CO2."),
    ]
    
    print("\nText Length | Latency (ms) | Duration (s) | Meets Target")
    print("-" * 65)
    
    for label, text in test_texts:
        result = await tts.synthesize(text)
        
        if result.success:
            meets_target = "✓" if result.latency < 100 else "✗"
            print(f"{label:11} | {result.latency:12.2f} | {result.duration:12.2f} | {meets_target:12}")
        else:
            print(f"{label:11} | Failed: {result.error_message}")


async def test_available_voices():
    """List all available neural voices."""
    print("\n=== Available Neural Voices ===")
    
    subscription_key = os.getenv("AZURE_SPEECH_KEY")
    region = os.getenv("AZURE_SPEECH_REGION", "eastus")
    
    if not subscription_key:
        print("ERROR: AZURE_SPEECH_KEY not set in .env file")
        return
    
    tts = create_azure_tts(
        subscription_key=subscription_key,
        region=region
    )
    
    # Get voices by language
    languages = ["en-US", "en-GB", "es-ES", "fr-FR", "de-DE"]
    
    for lang in languages:
        voices = tts.get_available_voices(language=lang)
        print(f"\n{lang}: {len(voices)} voices")
        for voice in voices[:5]:  # Show first 5
            print(f"  - {voice}")
        if len(voices) > 5:
            print(f"  ... and {len(voices) - 5} more")


async def main():
    """Run all tests."""
    print("=" * 70)
    print("Azure Speech Services TTS Test Suite")
    print("=" * 70)
    
    try:
        # Run tests
        await test_basic_synthesis()
        await test_voice_customization()
        await test_multiple_voices()
        await test_latency_benchmark()
        await test_available_voices()
        
        print("\n" + "=" * 70)
        print("All tests completed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
