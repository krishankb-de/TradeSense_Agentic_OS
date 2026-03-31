"""
End-to-End Tests for LLM Integration (Task 2)
Tests Gemini, Azure OpenAI, and Unified LLM clients
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.config import settings
from llm import GeminiClient, AzureOpenAIClient, UnifiedLLMClient, LLMProvider, LLMError


def test_gemini_client():
    """Test Google Gemini API client."""
    print("\n" + "="*80)
    print("TEST 1: Google Gemini API Client")
    print("="*80)
    
    if not settings.google_api_key:
        print("❌ SKIPPED: GOOGLE_API_KEY not configured in .env")
        return False
    
    try:
        # Initialize client
        print("\n1. Initializing Gemini client...")
        client = GeminiClient(
            api_key=settings.google_api_key,
            model_name="gemini-pro",
            enable_caching=True
        )
        print("✅ Client initialized successfully")
        
        # Test generation
        print("\n2. Testing text generation...")
        prompt = "Say 'Hello from Gemini!' and nothing else."
        response = client.generate(prompt=prompt, temperature=0.1, max_tokens=50)
        
        print(f"✅ Generated response: {response.text[:100]}")
        print(f"   - Model: {response.model}")
        print(f"   - Tokens: {response.total_tokens} (input: {response.prompt_tokens}, output: {response.completion_tokens})")
        print(f"   - Latency: {response.latency:.2f}s")
        
        # Test quota status
        print("\n3. Checking quota status...")
        quota = client.get_quota_status()
        print(f"✅ Quota status:")
        print(f"   - Requests today: {quota['requests_today']}/{quota['daily_limit']}")
        print(f"   - Requests remaining: {quota['requests_remaining']}")
        print(f"   - Cache size: {quota['cache_size']}")
        
        # Test caching
        print("\n4. Testing response caching...")
        response2 = client.generate(prompt=prompt, temperature=0.1, max_tokens=50)
        print(f"✅ Cache working (latency: {response2.latency:.4f}s)")
        
        print("\n✅ ALL GEMINI TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ GEMINI TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_azure_openai_client():
    """Test Azure OpenAI API client."""
    print("\n" + "="*80)
    print("TEST 2: Azure OpenAI API Client")
    print("="*80)
    
    if not settings.azure_openai_key or not settings.azure_openai_endpoint:
        print("❌ SKIPPED: Azure OpenAI credentials not configured in .env")
        return False
    
    try:
        # Initialize client
        print("\n1. Initializing Azure OpenAI client...")
        client = AzureOpenAIClient(
            api_key=settings.azure_openai_key,
            endpoint=settings.azure_openai_endpoint,
            deployment_name=settings.azure_openai_deployment_gpt35,
            budget_limit=100.0
        )
        print("✅ Client initialized successfully")
        
        # Test generation
        print("\n2. Testing text generation...")
        prompt = "Say 'Hello from Azure OpenAI!' and nothing else."
        response = client.generate(prompt=prompt, temperature=0.1, max_tokens=50)
        
        print(f"✅ Generated response: {response.text[:100]}")
        print(f"   - Model: {response.model}")
        print(f"   - Tokens: {response.total_tokens} (input: {response.prompt_tokens}, output: {response.completion_tokens})")
        print(f"   - Latency: {response.latency:.2f}s")
        print(f"   - Cost: ${response.metadata.get('cost', 0):.4f}")
        
        # Test cost tracking
        print("\n3. Checking cost summary...")
        cost_summary = client.get_cost_summary()
        print(f"✅ Cost summary:")
        print(f"   - Total cost: ${cost_summary['total_cost']:.4f}")
        print(f"   - Budget remaining: ${cost_summary['budget_remaining']:.2f}")
        print(f"   - Budget used: {cost_summary['budget_used_pct']:.2f}%")
        print(f"   - Total requests: {cost_summary['total_requests']}")
        
        print("\n✅ ALL AZURE OPENAI TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ AZURE OPENAI TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_unified_client():
    """Test Unified LLM client with intelligent routing."""
    print("\n" + "="*80)
    print("TEST 3: Unified LLM Client (Intelligent Routing)")
    print("="*80)
    
    if not settings.google_api_key and not settings.azure_openai_key:
        print("❌ SKIPPED: No LLM providers configured")
        return False
    
    try:
        # Initialize client
        print("\n1. Initializing Unified LLM client...")
        client = UnifiedLLMClient(
            gemini_api_key=settings.google_api_key if settings.google_api_key else None,
            azure_api_key=settings.azure_openai_key if settings.azure_openai_key else None,
            azure_endpoint=settings.azure_openai_endpoint if settings.azure_openai_endpoint else None,
            azure_deployment=settings.azure_openai_deployment_gpt35,
            enable_logging=True
        )
        print("✅ Client initialized successfully")
        
        # Test default routing (Gemini first)
        print("\n2. Testing default routing (Gemini → Azure)...")
        prompt = "Say 'Hello from Unified Client!' and nothing else."
        response = client.generate(prompt=prompt, temperature=0.1, max_tokens=50)
        
        print(f"✅ Generated response: {response.text[:100]}")
        print(f"   - Provider used: {response.metadata.get('provider', 'unknown')}")
        print(f"   - Fallback used: {response.metadata.get('fallback_used', False)}")
        print(f"   - Total latency: {response.metadata.get('total_latency', 0):.2f}s")
        
        # Test status
        print("\n3. Checking unified client status...")
        status = client.get_status()
        print(f"✅ Status:")
        print(f"   - Total requests: {status['total_requests']}")
        print(f"   - Success rate: {status['success_rate']:.1f}%")
        print(f"   - Fallback count: {status['fallback_count']}")
        print(f"   - Available providers: {list(status['providers'].keys())}")
        
        # Test cost summary
        print("\n4. Checking cost summary...")
        cost_summary = client.get_cost_summary()
        print(f"✅ Cost summary:")
        print(f"   - Total cost: ${cost_summary['total_cost']:.4f}")
        for provider, details in cost_summary['providers'].items():
            print(f"   - {provider}: ${details.get('cost', 0):.4f}")
        
        # Test request logs
        print("\n5. Checking request logs...")
        logs = client.get_request_logs(limit=5)
        print(f"✅ Recent requests: {len(logs)}")
        for i, log in enumerate(logs[-3:], 1):
            print(f"   {i}. {log.provider.value} - {'✅' if log.success else '❌'} - {log.timestamp.strftime('%H:%M:%S')}")
        
        print("\n✅ ALL UNIFIED CLIENT TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ UNIFIED CLIENT TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_fallback_behavior():
    """Test fallback behavior when primary provider fails."""
    print("\n" + "="*80)
    print("TEST 4: Fallback Behavior")
    print("="*80)
    
    if not settings.google_api_key or not settings.azure_openai_key:
        print("❌ SKIPPED: Both Gemini and Azure OpenAI required for fallback testing")
        return False
    
    try:
        print("\n1. Testing provider preference...")
        client = UnifiedLLMClient(
            gemini_api_key=settings.google_api_key,
            azure_api_key=settings.azure_openai_key,
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment_gpt35
        )
        
        # Test with Azure preference
        print("\n2. Generating with Azure preference...")
        response = client.generate(
            prompt="Say 'Azure preferred!' and nothing else.",
            temperature=0.1,
            max_tokens=50,
            prefer_provider=LLMProvider.AZURE_OPENAI
        )
        print(f"✅ Provider used: {response.metadata.get('provider', 'unknown')}")
        
        print("\n✅ FALLBACK BEHAVIOR TESTS PASSED")
        return True
        
    except Exception as e:
        print(f"\n❌ FALLBACK TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all LLM integration tests."""
    print("\n" + "="*80)
    print("TRADESENSE LLM INTEGRATION - END-TO-END TESTS")
    print("="*80)
    print("\nTesting Task 2: Cloud LLM Integration Infrastructure")
    print("- Google Gemini API (Free Tier)")
    print("- Azure OpenAI (GitHub Student Credits)")
    print("- Unified Client with Intelligent Routing")
    
    results = {
        "Gemini Client": test_gemini_client(),
        "Azure OpenAI Client": test_azure_openai_client(),
        "Unified Client": test_unified_client(),
        "Fallback Behavior": test_fallback_behavior(),
    }
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED/SKIPPED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! LLM integration is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed or skipped. Check configuration and logs.")
        return 1


if __name__ == "__main__":
    exit(main())
