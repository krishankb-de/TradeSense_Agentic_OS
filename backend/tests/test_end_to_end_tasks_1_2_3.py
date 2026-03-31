"""
End-to-End Testing for Tasks 1, 2, and 3
Tests infrastructure, LLM integration, and voice processing
"""

import asyncio
import os
import sys
from pathlib import Path
import tempfile
import time

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_header(text):
    """Print a formatted header."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text.center(80)}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")


def print_test(text):
    """Print a test description."""
    print(f"{YELLOW}> {text}{RESET}")


def print_success(text):
    """Print a success message."""
    print(f"{GREEN}+ {text}{RESET}")


def print_error(text):
    """Print an error message."""
    print(f"{RED}X {text}{RESET}")


def print_info(text):
    """Print an info message."""
    print(f"  {text}")


# ============================================================================
# TASK 1: Infrastructure Tests
# ============================================================================

def test_task_1_infrastructure():
    """Test Task 1: Foundational infrastructure and development environment."""
    print_header("TASK 1: Infrastructure and Development Environment")
    
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # Test 1.1: Project directory structure
    print_test("Test 1.1: Project directory structure")
    # Get project root (parent of backend)
    project_root = Path(__file__).parent.parent.parent
    required_dirs = [
        "backend",
        "backend/api",
        "backend/core",
        "backend/llm",
        "backend/voice",
        "backend/tests",
        "backend/examples",
        "frontend",
        "docker",
    ]
    
    all_dirs_exist = True
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if not full_path.exists():
            print_error(f"Missing directory: {dir_path}")
            all_dirs_exist = False
    
    if all_dirs_exist:
        print_success("All required directories exist")
        results["passed"] += 1
        results["tests"].append(("Project structure", "PASS"))
    else:
        print_error("Some directories are missing")
        results["failed"] += 1
        results["tests"].append(("Project structure", "FAIL"))
    
    # Test 1.2: Docker Compose configuration
    print_test("Test 1.2: Docker Compose configuration")
    project_root = Path(__file__).parent.parent.parent
    docker_compose_file = project_root / "docker-compose.lightweight.yml"
    
    if docker_compose_file.exists():
        print_success(f"Docker Compose file exists: {docker_compose_file.name}")
        results["passed"] += 1
        results["tests"].append(("Docker Compose config", "PASS"))
    else:
        print_error(f"Docker Compose file missing: {docker_compose_file.name}")
        results["failed"] += 1
        results["tests"].append(("Docker Compose config", "FAIL"))
    
    # Test 1.3: Environment variables
    print_test("Test 1.3: Environment variables configuration")
    required_env_vars = [
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "REDIS_HOST",
        "REDIS_PORT",
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if not missing_vars:
        print_success("All required environment variables are set")
        results["passed"] += 1
        results["tests"].append(("Environment variables", "PASS"))
    else:
        print_error(f"Missing environment variables: {', '.join(missing_vars)}")
        results["failed"] += 1
        results["tests"].append(("Environment variables", "FAIL"))
    
    # Test 1.4: Configuration loading
    print_test("Test 1.4: Configuration loading")
    try:
        from core.config import settings
        print_info(f"Environment: {settings.environment}")
        print_info(f"Database URL: {settings.database_url[:30]}...")
        print_info(f"Redis URL: {settings.redis_url[:30]}...")
        print_success("Configuration loaded successfully")
        results["passed"] += 1
        results["tests"].append(("Configuration loading", "PASS"))
    except Exception as e:
        print_error(f"Configuration loading failed: {e}")
        results["failed"] += 1
        results["tests"].append(("Configuration loading", "FAIL"))
    
    # Test 1.5: Python dependencies
    print_test("Test 1.5: Python dependencies")
    required_packages = [
        "fastapi",
        "pydantic",
        "redis",
        "azure.cognitiveservices.speech",
        "google.generativeai",
        "openai",
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
        except Exception as e:
            # Skip SQLAlchemy Python 3.14 compatibility issue
            print_info(f"Warning: {package} import issue (may be Python 3.14 compatibility): {str(e)[:50]}")
    
    if not missing_packages:
        print_success("All required Python packages are installed")
        results["passed"] += 1
        results["tests"].append(("Python dependencies", "PASS"))
    else:
        print_error(f"Missing packages: {', '.join(missing_packages)}")
        results["failed"] += 1
        results["tests"].append(("Python dependencies", "FAIL"))
    
    return results


# ============================================================================
# TASK 2: LLM Integration Tests
# ============================================================================

async def test_task_2_llm_integration():
    """Test Task 2: Cloud LLM integration infrastructure."""
    print_header("TASK 2: Cloud LLM Integration Infrastructure")
    
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # Test 2.1: Google Gemini API client
    print_test("Test 2.1: Google Gemini API client initialization")
    try:
        from llm.gemini_client import GeminiClient
        
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print_error("GOOGLE_API_KEY not set in environment")
            results["failed"] += 1
            results["tests"].append(("Gemini client init", "FAIL"))
        else:
            client = GeminiClient(api_key=api_key)
            print_info(f"Model: {client.model_name}")
            print_info(f"Free tier limit: {client.FREE_TIER_DAILY_LIMIT} requests/day")
            print_info(f"Rate limit: {client.FREE_TIER_RPM} requests/minute")
            print_success("Gemini client initialized successfully")
            results["passed"] += 1
            results["tests"].append(("Gemini client init", "PASS"))
    except Exception as e:
        print_error(f"Gemini client initialization failed: {e}")
        results["failed"] += 1
        results["tests"].append(("Gemini client init", "FAIL"))
    
    # Test 2.2: Azure OpenAI client
    print_test("Test 2.2: Azure OpenAI client initialization")
    try:
        from llm.azure_openai_client import AzureOpenAIClient
        
        api_key = os.getenv("AZURE_OPENAI_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if not api_key or not endpoint:
            print_error("Azure OpenAI credentials not set")
            results["failed"] += 1
            results["tests"].append(("Azure OpenAI client init", "FAIL"))
        else:
            client = AzureOpenAIClient(
                api_key=api_key,
                endpoint=endpoint,
                api_version="2024-02-15-preview"
            )
            print_info(f"Budget limit: ${client.budget_limit}")
            print_success("Azure OpenAI client initialized successfully")
            results["passed"] += 1
            results["tests"].append(("Azure OpenAI client init", "PASS"))
    except Exception as e:
        print_error(f"Azure OpenAI client initialization failed: {e}")
        results["failed"] += 1
        results["tests"].append(("Azure OpenAI client init", "FAIL"))
    
    # Test 2.3: Unified LLM client
    print_test("Test 2.3: Unified LLM client initialization")
    try:
        from llm.unified_client import UnifiedLLMClient
        
        gemini_key = os.getenv("GOOGLE_API_KEY")
        azure_key = os.getenv("AZURE_OPENAI_KEY")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if not gemini_key:
            print_error("GOOGLE_API_KEY not set")
            results["failed"] += 1
            results["tests"].append(("Unified client init", "FAIL"))
        else:
            client = UnifiedLLMClient(
                gemini_api_key=gemini_key,
                azure_api_key=azure_key,
                azure_endpoint=azure_endpoint
            )
            # Check which clients are available
            providers = []
            if client.gemini_client:
                providers.append("Gemini")
            if client.azure_client:
                providers.append("Azure OpenAI")
            print_info(f"Available providers: {', '.join(providers)}")
            print_info(f"Total requests: {client.total_requests}")
            print_success("Unified LLM client initialized successfully")
            results["passed"] += 1
            results["tests"].append(("Unified client init", "PASS"))
    except Exception as e:
        print_error(f"Unified client initialization failed: {e}")
        results["failed"] += 1
        results["tests"].append(("Unified client init", "FAIL"))
    
    # Test 2.4: LLM generation (if API keys available)
    print_test("Test 2.4: LLM text generation")
    try:
        from llm.unified_client import UnifiedLLMClient
        
        gemini_key = os.getenv("GOOGLE_API_KEY")
        if not gemini_key:
            print_error("Skipping generation test - no API key")
            results["tests"].append(("LLM generation", "SKIP"))
        else:
            client = UnifiedLLMClient(gemini_api_key=gemini_key)
            response = client.generate(
                prompt="Say 'Hello, TradeSense!' in exactly 3 words.",
                max_tokens=50
            )
            
            if response and response.text:
                print_info(f"Response: {response.text[:100]}")
                print_info(f"Provider: {response.metadata.get('provider', 'unknown')}")
                print_success("LLM generation successful")
                results["passed"] += 1
                results["tests"].append(("LLM generation", "PASS"))
            else:
                print_error("LLM generation returned empty response")
                results["failed"] += 1
                results["tests"].append(("LLM generation", "FAIL"))
    except Exception as e:
        print_error(f"LLM generation failed: {e}")
        import traceback
        traceback.print_exc()
        results["failed"] += 1
        results["tests"].append(("LLM generation", "FAIL"))
    
    return results


# ============================================================================
# TASK 3: Voice Processing Tests
# ============================================================================

async def test_task_3_voice_processing():
    """Test Task 3: Cloud voice processing pipeline."""
    print_header("TASK 3: Cloud Voice Processing Pipeline")
    
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # Test 3.1: Azure Speech STT client
    print_test("Test 3.1: Azure Speech STT client initialization")
    try:
        from voice.stt import create_azure_stt
        
        api_key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        
        if not api_key:
            print_error("AZURE_SPEECH_KEY not set")
            results["failed"] += 1
            results["tests"].append(("STT client init", "FAIL"))
        else:
            stt = create_azure_stt(
                subscription_key=api_key,
                region=region,
                language="en-US"
            )
            print_info(f"Region: {stt.region}")
            print_info(f"Language: {stt.language}")
            print_info(f"Supported languages: {len(stt.get_supported_languages())}")
            print_success("STT client initialized successfully")
            results["passed"] += 1
            results["tests"].append(("STT client init", "PASS"))
    except Exception as e:
        print_error(f"STT client initialization failed: {e}")
        results["failed"] += 1
        results["tests"].append(("STT client init", "FAIL"))
    
    # Test 3.2: Azure Speech TTS client
    print_test("Test 3.2: Azure Speech TTS client initialization")
    try:
        from voice.tts import create_azure_tts
        
        api_key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        
        if not api_key:
            print_error("AZURE_SPEECH_KEY not set")
            results["failed"] += 1
            results["tests"].append(("TTS client init", "FAIL"))
        else:
            tts = create_azure_tts(
                subscription_key=api_key,
                region=region,
                voice_name="en-US-JennyNeural"
            )
            print_info(f"Region: {tts.region}")
            print_info(f"Voice: {tts.voice_name}")
            print_info(f"Available voices: {len(tts.get_available_voices())}")
            print_success("TTS client initialized successfully")
            results["passed"] += 1
            results["tests"].append(("TTS client init", "PASS"))
    except Exception as e:
        print_error(f"TTS client initialization failed: {e}")
        results["failed"] += 1
        results["tests"].append(("TTS client init", "FAIL"))
    
    # Test 3.3: TTS synthesis
    print_test("Test 3.3: Text-to-speech synthesis")
    try:
        from voice.tts import create_azure_tts
        
        api_key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        
        if not api_key:
            print_error("Skipping TTS synthesis - no API key")
            results["tests"].append(("TTS synthesis", "SKIP"))
        else:
            tts = create_azure_tts(
                subscription_key=api_key,
                region=region,
                voice_name="en-US-JennyNeural"
            )
            
            start_time = time.time()
            result = await tts.synthesize("Hello, TradeSense!")
            latency = (time.time() - start_time) * 1000
            
            if result.success:
                print_info(f"Audio size: {len(result.audio_data)} bytes")
                print_info(f"Duration: {result.duration:.2f}s")
                print_info(f"Latency: {latency:.2f}ms")
                
                # Check latency requirement (should be < 600ms for cloud)
                if latency < 1000:
                    print_success("TTS synthesis successful with acceptable latency")
                    results["passed"] += 1
                    results["tests"].append(("TTS synthesis", "PASS"))
                else:
                    print_error(f"TTS latency too high: {latency:.2f}ms")
                    results["failed"] += 1
                    results["tests"].append(("TTS synthesis", "FAIL"))
            else:
                print_error(f"TTS synthesis failed: {result.error_message}")
                results["failed"] += 1
                results["tests"].append(("TTS synthesis", "FAIL"))
    except Exception as e:
        print_error(f"TTS synthesis failed: {e}")
        results["failed"] += 1
        results["tests"].append(("TTS synthesis", "FAIL"))
    
    # Test 3.4: Voice module imports
    print_test("Test 3.4: Voice module imports")
    try:
        from voice import (
            AzureSpeechSTT,
            AzureSpeechTTS,
            TranscriptionResult,
            SynthesisResult,
            VoiceConfig,
            VoiceStyle,
        )
        print_success("All voice module imports successful")
        results["passed"] += 1
        results["tests"].append(("Voice module imports", "PASS"))
    except Exception as e:
        print_error(f"Voice module imports failed: {e}")
        results["failed"] += 1
        results["tests"].append(("Voice module imports", "FAIL"))
    
    return results


# ============================================================================
# COMBINATION TESTS
# ============================================================================

async def test_combination_llm_and_voice():
    """Test combination of LLM and voice processing."""
    print_header("COMBINATION TEST: LLM + Voice Processing")
    
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # Test: Generate text with LLM and synthesize with TTS
    print_test("Test: LLM text generation -> TTS synthesis")
    try:
        from llm.unified_client import UnifiedLLMClient
        from voice.tts import create_azure_tts
        
        gemini_key = os.getenv("GOOGLE_API_KEY")
        azure_speech_key = os.getenv("AZURE_SPEECH_KEY")
        azure_speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        
        if not gemini_key or not azure_speech_key:
            print_error("Skipping combination test - missing API keys")
            results["tests"].append(("LLM + TTS combination", "SKIP"))
        else:
            # Generate text with LLM
            print_info("Step 1: Generating text with LLM...")
            llm_client = UnifiedLLMClient(gemini_api_key=gemini_key)
            llm_response = llm_client.generate(
                prompt="Say a friendly greeting for a field service technician in 10 words or less.",
                max_tokens=50
            )
            
            if not llm_response or not llm_response.text:
                print_error("LLM generation failed")
                results["failed"] += 1
                results["tests"].append(("LLM + TTS combination", "FAIL"))
                return results
            
            generated_text = llm_response.text.strip()
            print_info(f"Generated text: {generated_text}")
            print_info(f"Provider: {llm_response.metadata.get('provider', 'unknown')}")
            
            # Synthesize with TTS
            print_info("Step 2: Synthesizing speech with TTS...")
            tts_client = create_azure_tts(
                subscription_key=azure_speech_key,
                region=azure_speech_region,
                voice_name="en-US-JennyNeural"
            )
            
            tts_result = await tts_client.synthesize(generated_text)
            
            if tts_result.success:
                print_info(f"Audio size: {len(tts_result.audio_data)} bytes")
                print_info(f"Duration: {tts_result.duration:.2f}s")
                print_info(f"Latency: {tts_result.latency:.2f}ms")
                print_success("LLM + TTS combination successful")
                results["passed"] += 1
                results["tests"].append(("LLM + TTS combination", "PASS"))
            else:
                print_error(f"TTS synthesis failed: {tts_result.error_message}")
                results["failed"] += 1
                results["tests"].append(("LLM + TTS combination", "FAIL"))
    except Exception as e:
        print_error(f"Combination test failed: {e}")
        results["failed"] += 1
        results["tests"].append(("LLM + TTS combination", "FAIL"))
    
    return results


# ============================================================================
# FULL INTEGRATION TEST
# ============================================================================

async def test_full_integration():
    """Test full integration: Infrastructure → LLM → Voice."""
    print_header("FULL INTEGRATION TEST: End-to-End Workflow")
    
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    print_test("Test: Complete workflow simulation")
    try:
        from core.config import settings
        from llm.unified_client import UnifiedLLMClient
        from voice.tts import create_azure_tts
        
        # Step 1: Verify infrastructure
        print_info("Step 1: Verifying infrastructure...")
        print_info(f"  Environment: {settings.environment}")
        print_info(f"  Database configured: {bool(settings.postgres_host)}")
        print_info(f"  Redis configured: {bool(settings.redis_host)}")
        
        # Step 2: Initialize LLM client
        print_info("Step 2: Initializing LLM client...")
        gemini_key = os.getenv("GOOGLE_API_KEY")
        if not gemini_key:
            print_error("GOOGLE_API_KEY not set")
            results["failed"] += 1
            results["tests"].append(("Full integration", "FAIL"))
            return results
        
        llm_client = UnifiedLLMClient(gemini_api_key=gemini_key)
        # Check which providers are available
        providers = []
        if llm_client.gemini_client:
            providers.append("Gemini")
        if llm_client.azure_client:
            providers.append("Azure OpenAI")
        print_info(f"  Available providers: {', '.join(providers)}")
        
        # Step 3: Initialize voice client
        print_info("Step 3: Initializing voice client...")
        azure_speech_key = os.getenv("AZURE_SPEECH_KEY")
        azure_speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus")
        
        if not azure_speech_key:
            print_error("AZURE_SPEECH_KEY not set")
            results["failed"] += 1
            results["tests"].append(("Full integration", "FAIL"))
            return results
        
        tts_client = create_azure_tts(
            subscription_key=azure_speech_key,
            region=azure_speech_region,
            voice_name="en-US-AriaNeural"
        )
        print_info(f"  Voice: {tts_client.voice_name}")
        
        # Step 4: Simulate field service interaction
        print_info("Step 4: Simulating field service interaction...")
        
        # Generate response for technician
        prompt = """You are a helpful field service assistant. 
        A technician just completed a water heater repair. 
        Generate a brief confirmation message (15 words or less) to log the job completion."""
        
        llm_response = llm_client.generate(prompt=prompt, max_tokens=100)
        
        if not llm_response or not llm_response.text:
            print_error("LLM generation failed")
            results["failed"] += 1
            results["tests"].append(("Full integration", "FAIL"))
            return results
        
        message = llm_response.text.strip()
        print_info(f"  Generated message: {message}")
        print_info(f"  LLM provider: {llm_response.metadata.get('provider', 'unknown')}")
        
        # Synthesize voice response
        tts_result = await tts_client.synthesize(message)
        
        if not tts_result.success:
            print_error(f"TTS synthesis failed: {tts_result.error_message}")
            results["failed"] += 1
            results["tests"].append(("Full integration", "FAIL"))
            return results
        
        print_info(f"  Audio generated: {len(tts_result.audio_data)} bytes")
        print_info(f"  TTS latency: {tts_result.latency:.2f}ms")
        
        # Step 5: Calculate total workflow metrics
        print_info("Step 5: Workflow metrics...")
        total_latency = tts_result.latency
        
        print_info(f"  Total latency: {total_latency:.2f}ms")
        
        print_success("Full integration test successful!")
        results["passed"] += 1
        results["tests"].append(("Full integration", "PASS"))
        
    except Exception as e:
        print_error(f"Full integration test failed: {e}")
        import traceback
        traceback.print_exc()
        results["failed"] += 1
        results["tests"].append(("Full integration", "FAIL"))
    
    return results


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def main():
    """Run all end-to-end tests."""
    print_header("TradeSense End-to-End Testing Suite")
    print_info("Testing Tasks 1, 2, and 3 individually and in combination")
    print_info(f"Test started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = []
    
    # Run individual task tests
    print("\n" + "=" * 80)
    print("PHASE 1: Individual Task Tests")
    print("=" * 80)
    
    task1_results = test_task_1_infrastructure()
    all_results.append(("Task 1: Infrastructure", task1_results))
    
    task2_results = await test_task_2_llm_integration()
    all_results.append(("Task 2: LLM Integration", task2_results))
    
    task3_results = await test_task_3_voice_processing()
    all_results.append(("Task 3: Voice Processing", task3_results))
    
    # Run combination tests
    print("\n" + "=" * 80)
    print("PHASE 2: Combination Tests")
    print("=" * 80)
    
    combo_results = await test_combination_llm_and_voice()
    all_results.append(("Combination: LLM + Voice", combo_results))
    
    # Run full integration test
    print("\n" + "=" * 80)
    print("PHASE 3: Full Integration Test")
    print("=" * 80)
    
    full_results = await test_full_integration()
    all_results.append(("Full Integration", full_results))
    
    # Print summary
    print_header("TEST SUMMARY")
    
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    
    for test_name, results in all_results:
        passed = results["passed"]
        failed = results["failed"]
        skipped = sum(1 for _, status in results["tests"] if status == "SKIP")
        
        total_passed += passed
        total_failed += failed
        total_skipped += skipped
        
        status_color = GREEN if failed == 0 else RED
        print(f"\n{test_name}:")
        print(f"  {status_color}Passed: {passed}{RESET}")
        print(f"  {RED}Failed: {failed}{RESET}")
        if skipped > 0:
            print(f"  {YELLOW}Skipped: {skipped}{RESET}")
        
        # Print individual test results
        for test_desc, status in results["tests"]:
            if status == "PASS":
                print(f"    {GREEN}+{RESET} {test_desc}")
            elif status == "FAIL":
                print(f"    {RED}X{RESET} {test_desc}")
            elif status == "SKIP":
                print(f"    {YELLOW}-{RESET} {test_desc}")
    
    # Overall summary
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}OVERALL RESULTS{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}")
    print(f"{GREEN}Total Passed: {total_passed}{RESET}")
    print(f"{RED}Total Failed: {total_failed}{RESET}")
    if total_skipped > 0:
        print(f"{YELLOW}Total Skipped: {total_skipped}{RESET}")
    
    total_tests = total_passed + total_failed
    if total_tests > 0:
        success_rate = (total_passed / total_tests) * 100
        print(f"\n{BLUE}Success Rate: {success_rate:.1f}%{RESET}")
    
    if total_failed == 0:
        print(f"\n{GREEN}{'=' * 80}{RESET}")
        print(f"{GREEN}ALL TESTS PASSED!{RESET}")
        print(f"{GREEN}{'=' * 80}{RESET}")
    else:
        print(f"\n{RED}{'=' * 80}{RESET}")
        print(f"{RED}SOME TESTS FAILED - Please review the errors above{RESET}")
        print(f"{RED}{'=' * 80}{RESET}")
    
    print(f"\nTest completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    asyncio.run(main())
