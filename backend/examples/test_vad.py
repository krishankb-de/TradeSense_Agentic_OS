"""
Simple test script for Azure Speech VAD
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from voice.vad import (
    AzureSpeechVAD,
    VADConfig,
    VADState,
    create_azure_vad,
)

# Color codes
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_test(name):
    print(f"\n{BLUE}> Test: {name}{RESET}")


def print_pass(msg):
    print(f"{GREEN}  + {msg}{RESET}")


def print_fail(msg):
    print(f"{RED}  X {msg}{RESET}")


def test_vad_initialization():
    """Test VAD initialization."""
    print_test("VAD Initialization")
    
    vad = create_azure_vad()
    
    assert vad is not None, "VAD should be created"
    assert vad.config.sensitivity == 0.5, "Default sensitivity should be 0.5"
    assert vad.config.adaptive_threshold is True, "Adaptive threshold should be enabled"
    assert vad.current_state == VADState.SILENCE, "Initial state should be SILENCE"
    
    print_pass("VAD initialized successfully")
    print_pass(f"Sensitivity: {vad.config.sensitivity}")
    print_pass(f"Adaptive threshold: {vad.config.adaptive_threshold}")
    print_pass(f"Initial state: {vad.current_state.value}")


def test_vad_speech_detection():
    """Test basic speech detection."""
    print_test("Speech Detection")
    
    speech_events = {"started": [], "ended": []}
    
    def on_start(timestamp):
        speech_events["started"].append(timestamp)
    
    def on_end(timestamp):
        speech_events["ended"].append(timestamp)
    
    vad = create_azure_vad(
        sensitivity=0.5,
        on_speech_start=on_start,
        on_speech_end=on_end,
    )
    
    # Simulate audio levels
    timestamp = 0.0
    
    # Silence
    state = vad.process_audio_level(0.3, timestamp)
    assert state == VADState.SILENCE, "Should detect silence"
    print_pass(f"Silence detected at {timestamp}s")
    
    # Speech starts
    timestamp += 0.05
    state = vad.process_audio_level(0.8, timestamp)
    print_pass(f"Audio level 0.8 at {timestamp}s -> State: {state.value}")
    
    # Continue speech
    timestamp += 0.15
    state = vad.process_audio_level(0.9, timestamp)
    assert state == VADState.SPEECH, "Should detect speech"
    assert len(speech_events["started"]) == 1, "Speech start event should fire"
    print_pass(f"Speech confirmed at {timestamp}s")
    
    # Speech continues
    timestamp += 0.1
    state = vad.process_audio_level(0.7, timestamp)
    assert state == VADState.SPEECH, "Speech should continue"
    print_pass(f"Speech continuing at {timestamp}s")
    
    # Silence starts
    timestamp += 0.1
    state = vad.process_audio_level(0.2, timestamp)
    print_pass(f"Low audio level at {timestamp}s -> State: {state.value}")
    
    # Silence continues (min silence duration met)
    timestamp += 0.6
    state = vad.process_audio_level(0.1, timestamp)
    assert state == VADState.SILENCE, "Should return to silence"
    assert len(speech_events["ended"]) == 1, "Speech end event should fire"
    print_pass(f"Speech ended at {timestamp}s")
    
    print_pass(f"Total speech events: {len(speech_events['started'])} starts, {len(speech_events['ended'])} ends")


def test_vad_adaptive_threshold():
    """Test adaptive threshold for noisy environments."""
    print_test("Adaptive Threshold")
    
    vad = create_azure_vad(sensitivity=0.5, adaptive=True)
    
    # Normal noise level
    vad.update_ambient_noise(50.0)
    threshold1 = vad.get_adaptive_threshold()
    print_pass(f"Normal noise (50dB): threshold = {threshold1}")
    assert threshold1 == 0.5, "Threshold should remain at 0.5"
    
    # High noise level (exceeds 60dB threshold)
    vad.update_ambient_noise(70.0)
    vad.update_ambient_noise(75.0)
    threshold2 = vad.get_adaptive_threshold()
    print_pass(f"High noise (70-75dB): threshold = {threshold2}")
    assert threshold2 > 0.5, "Threshold should increase"
    assert threshold2 <= 1.0, "Threshold should not exceed 1.0"
    
    print_pass(f"Adaptive threshold working: {threshold1} -> {threshold2}")


def test_vad_speech_boundary():
    """Test speech boundary detection."""
    print_test("Speech Boundary Detection")
    
    speech_started = []
    
    def on_start(timestamp):
        speech_started.append(timestamp)
    
    config = VADConfig(
        sensitivity=0.5,
        min_speech_duration_ms=100,
        boundary_detection=True,
    )
    
    vad = AzureSpeechVAD(config=config, on_speech_start=on_start)
    
    timestamp = 0.0
    
    # Very short speech burst (< 100ms)
    state = vad.process_audio_level(0.8, timestamp)
    print_pass(f"Short burst at {timestamp}s -> State: {state.value}")
    
    timestamp += 0.05  # 50ms later
    state = vad.process_audio_level(0.2, timestamp)
    assert state == VADState.SILENCE, "Should reject short burst"
    assert len(speech_started) == 0, "No speech start event for short burst"
    print_pass("Short burst rejected (< 100ms)")
    
    # Longer speech (> 100ms)
    timestamp += 0.1
    state = vad.process_audio_level(0.9, timestamp)
    
    timestamp += 0.15  # 150ms later
    state = vad.process_audio_level(0.8, timestamp)
    assert state == VADState.SPEECH, "Should confirm longer speech"
    assert len(speech_started) == 1, "Speech start event should fire"
    print_pass("Longer speech confirmed (> 100ms)")


def test_vad_reset():
    """Test VAD state reset."""
    print_test("VAD Reset")
    
    # Disable boundary detection for simpler test
    config = VADConfig(
        sensitivity=0.5,
        boundary_detection=False,  # Disable for simpler test
    )
    vad = AzureSpeechVAD(config=config)
    
    # Trigger speech
    state1 = vad.process_audio_level(0.9, 0.0)
    print_pass(f"First audio level: state = {state1.value}")
    
    state2 = vad.process_audio_level(0.9, 0.15)
    print_pass(f"Second audio level: state = {state2.value}")
    
    assert vad.current_state == VADState.SPEECH, f"Should be in speech state, but got {vad.current_state.value}"
    print_pass("Speech state activated")
    
    # Reset
    vad.reset()
    assert vad.current_state == VADState.SILENCE, "Should reset to silence"
    assert vad.speech_start_time is None, "Speech start time should be cleared"
    assert vad.silence_start_time is None, "Silence start time should be cleared"
    print_pass("VAD state reset successfully")


def main():
    """Run all tests."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}Azure Speech VAD Tests{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}")
    
    tests = [
        test_vad_initialization,
        test_vad_speech_detection,
        test_vad_adaptive_threshold,
        test_vad_speech_boundary,
        test_vad_reset,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print_fail(f"Test failed: {e}")
            failed += 1
        except Exception as e:
            print_fail(f"Test error: {e}")
            failed += 1
    
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}Test Results{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}")
    print(f"{GREEN}Passed: {passed}{RESET}")
    print(f"{RED}Failed: {failed}{RESET}")
    print(f"{BLUE}Total: {passed + failed}{RESET}")
    
    if failed == 0:
        print(f"\n{GREEN}All tests passed!{RESET}\n")
    else:
        print(f"\n{RED}Some tests failed!{RESET}\n")


if __name__ == "__main__":
    main()
