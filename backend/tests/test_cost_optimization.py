"""
Tests for Cloud Cost Optimization
Tests quota management, caching, cost tracking, and fallback routing
"""

import pytest
import time
from datetime import datetime, timedelta
from backend.llm.cost_optimizer import (
    CostOptimizer,
    ServiceType,
    QuotaLimit,
    CostRecord,
    BudgetAlert,
    get_cost_optimizer,
    initialize_cost_optimizer,
)
from backend.voice.cost_tracker import (
    SpeechCostTracker,
    SpeechUsageRecord,
    get_speech_cost_tracker,
    initialize_speech_cost_tracker,
)


class TestCostOptimizer:
    """Test cost optimizer functionality."""
    
    def test_initialization(self):
        """Test cost optimizer initialization."""
        optimizer = CostOptimizer(
            cache_ttl=1800,
            enable_caching=True,
            gemini_daily_limit=1500,
            azure_budget=100.0,
            azure_alert_threshold=0.8,
        )
        
        assert optimizer.cache_ttl == 1800
        assert optimizer.enable_caching is True
        assert ServiceType.GEMINI in optimizer.quotas
        assert optimizer.quotas[ServiceType.GEMINI].daily_limit == 1500
        assert ServiceType.AZURE_OPENAI in optimizer.budget_alerts
        assert optimizer.budget_alerts[ServiceType.AZURE_OPENAI].budget_limit == 100.0
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        optimizer = CostOptimizer()
        
        key1 = optimizer._generate_cache_key(
            ServiceType.GEMINI,
            "generate",
            prompt="test",
            temperature=0.7
        )
        key2 = optimizer._generate_cache_key(
            ServiceType.GEMINI,
            "generate",
            prompt="test",
            temperature=0.7
        )
        key3 = optimizer._generate_cache_key(
            ServiceType.GEMINI,
            "generate",
            prompt="different",
            temperature=0.7
        )
        
        assert key1 == key2  # Same parameters should generate same key
        assert key1 != key3  # Different parameters should generate different key
    
    def test_caching(self):
        """Test response caching."""
        optimizer = CostOptimizer(enable_caching=True, cache_ttl=2)
        
        # Cache a response
        response = {"text": "test response"}
        optimizer.cache_response(
            ServiceType.GEMINI,
            "generate",
            response,
            prompt="test"
        )
        
        # Retrieve cached response
        cached = optimizer.get_cached_response(
            ServiceType.GEMINI,
            "generate",
            prompt="test"
        )
        
        assert cached == response
        assert optimizer.cache_hits == 1
        assert optimizer.cache_misses == 0
        
        # Test cache miss
        cached = optimizer.get_cached_response(
            ServiceType.GEMINI,
            "generate",
            prompt="different"
        )
        
        assert cached is None
        assert optimizer.cache_misses == 1
    
    def test_cache_expiration(self):
        """Test cache expiration."""
        optimizer = CostOptimizer(enable_caching=True, cache_ttl=1)
        
        # Cache a response
        response = {"text": "test response"}
        optimizer.cache_response(
            ServiceType.GEMINI,
            "generate",
            response,
            prompt="test"
        )
        
        # Retrieve immediately (should hit)
        cached = optimizer.get_cached_response(
            ServiceType.GEMINI,
            "generate",
            prompt="test"
        )
        assert cached == response
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Retrieve after expiration (should miss)
        cached = optimizer.get_cached_response(
            ServiceType.GEMINI,
            "generate",
            prompt="test"
        )
        assert cached is None
    
    def test_quota_checking(self):
        """Test quota checking."""
        optimizer = CostOptimizer(gemini_daily_limit=10)
        
        # Should be within quota initially
        within_quota, reason = optimizer.check_quota(ServiceType.GEMINI)
        assert within_quota is True
        
        # Increment quota to limit
        for _ in range(10):
            optimizer.increment_quota(ServiceType.GEMINI)
        
        # Should exceed quota now
        within_quota, reason = optimizer.check_quota(ServiceType.GEMINI)
        assert within_quota is False
        assert "Daily limit exceeded" in reason
    
    def test_quota_reset(self):
        """Test quota reset after 24 hours."""
        optimizer = CostOptimizer(gemini_daily_limit=10)
        
        # Use up quota
        for _ in range(10):
            optimizer.increment_quota(ServiceType.GEMINI)
        
        # Manually reset time to simulate 24 hours passing
        quota = optimizer.quotas[ServiceType.GEMINI]
        quota.last_reset_time = datetime.now() - timedelta(days=1, seconds=1)
        
        # Check quota (should reset)
        within_quota, reason = optimizer.check_quota(ServiceType.GEMINI)
        assert within_quota is True
        assert quota.current_daily_usage == 0
    
    def test_budget_checking(self):
        """Test budget checking."""
        optimizer = CostOptimizer(azure_budget=10.0)
        
        # Should be within budget initially
        within_budget, reason = optimizer.check_budget(ServiceType.AZURE_OPENAI, 5.0)
        assert within_budget is True
        
        # Record cost
        optimizer.record_cost(ServiceType.AZURE_OPENAI, "generate", 5.0)
        
        # Should still be within budget
        within_budget, reason = optimizer.check_budget(ServiceType.AZURE_OPENAI, 4.0)
        assert within_budget is True
        
        # Should exceed budget
        within_budget, reason = optimizer.check_budget(ServiceType.AZURE_OPENAI, 6.0)
        assert within_budget is False
        assert "Budget exceeded" in reason
    
    def test_budget_alert(self):
        """Test budget alert triggering."""
        optimizer = CostOptimizer(azure_budget=10.0, azure_alert_threshold=0.8)
        
        alert = optimizer.budget_alerts[ServiceType.AZURE_OPENAI]
        assert alert.alert_sent is False
        
        # Record cost below threshold
        optimizer.record_cost(ServiceType.AZURE_OPENAI, "generate", 7.0)
        assert alert.alert_sent is False
        
        # Record cost above threshold
        optimizer.check_budget(ServiceType.AZURE_OPENAI, 1.5)
        assert alert.alert_sent is True
    
    def test_cost_recording(self):
        """Test cost recording."""
        optimizer = CostOptimizer()
        
        # Record costs
        optimizer.record_cost(ServiceType.GEMINI, "generate", 0.0, tokens_used=100)
        optimizer.record_cost(ServiceType.AZURE_OPENAI, "generate", 0.05, tokens_used=500)
        optimizer.record_cost(ServiceType.AZURE_OPENAI, "generate", 0.03, tokens_used=300)
        
        # Check totals
        assert optimizer.total_costs[ServiceType.GEMINI] == 0.0
        assert optimizer.total_costs[ServiceType.AZURE_OPENAI] == 0.08
        assert len(optimizer.cost_records) == 3
    
    def test_fallback_service(self):
        """Test fallback service selection."""
        optimizer = CostOptimizer()
        
        # Gemini should fallback to Azure OpenAI
        fallback = optimizer.get_fallback_service(ServiceType.GEMINI)
        assert fallback == ServiceType.AZURE_OPENAI
        assert optimizer.fallback_count == 1
        
        # Azure OpenAI has no fallback
        fallback = optimizer.get_fallback_service(ServiceType.AZURE_OPENAI)
        assert fallback is None
    
    def test_cost_summary(self):
        """Test cost summary generation."""
        optimizer = CostOptimizer()
        
        # Record some usage
        optimizer.record_cost(ServiceType.GEMINI, "generate", 0.0, tokens_used=100)
        optimizer.record_cost(ServiceType.AZURE_OPENAI, "generate", 0.05, tokens_used=500)
        optimizer.cache_response(ServiceType.GEMINI, "generate", {"text": "test"}, prompt="test")
        optimizer.get_cached_response(ServiceType.GEMINI, "generate", prompt="test")
        optimizer.increment_quota(ServiceType.GEMINI)
        
        summary = optimizer.get_cost_summary()
        
        assert "total_cost" in summary
        assert "costs_by_service" in summary
        assert "cache_stats" in summary
        assert "quota_stats" in summary
        assert "budget_stats" in summary
        assert "optimization_stats" in summary
        
        assert summary["total_cost"] == 0.05
        assert summary["cache_stats"]["hits"] == 1
        assert summary["quota_stats"]["gemini"]["daily_usage"] == 1
    
    def test_cost_records_filtering(self):
        """Test cost records filtering."""
        optimizer = CostOptimizer()
        
        # Record costs at different times
        optimizer.record_cost(ServiceType.GEMINI, "generate", 0.0)
        time.sleep(0.1)
        optimizer.record_cost(ServiceType.AZURE_OPENAI, "generate", 0.05)
        time.sleep(0.1)
        optimizer.record_cost(ServiceType.AZURE_OPENAI, "generate", 0.03)
        
        # Filter by service
        gemini_records = optimizer.get_cost_records(service=ServiceType.GEMINI)
        assert len(gemini_records) == 1
        
        azure_records = optimizer.get_cost_records(service=ServiceType.AZURE_OPENAI)
        assert len(azure_records) == 2
        
        # Filter by limit
        limited_records = optimizer.get_cost_records(limit=2)
        assert len(limited_records) == 2
    
    def test_cache_clearing(self):
        """Test cache clearing."""
        optimizer = CostOptimizer(enable_caching=True)
        
        # Cache some responses
        optimizer.cache_response(ServiceType.GEMINI, "generate", {"text": "test1"}, prompt="test1")
        optimizer.cache_response(ServiceType.GEMINI, "generate", {"text": "test2"}, prompt="test2")
        
        assert len(optimizer.response_cache) == 2
        
        # Clear cache
        optimizer.clear_cache()
        
        assert len(optimizer.response_cache) == 0
    
    def test_global_instance(self):
        """Test global cost optimizer instance."""
        # Initialize with custom config
        optimizer1 = initialize_cost_optimizer(cache_ttl=1800)
        assert optimizer1.cache_ttl == 1800
        
        # Get global instance
        optimizer2 = get_cost_optimizer()
        assert optimizer1 is optimizer2


class TestSpeechCostTracker:
    """Test speech cost tracker functionality."""
    
    def test_initialization(self):
        """Test speech cost tracker initialization."""
        tracker = SpeechCostTracker(
            budget_limit=50.0,
            alert_threshold=0.8,
        )
        
        assert tracker.budget_limit == 50.0
        assert tracker.alert_threshold == 0.8
        assert tracker.stt_total_seconds == 0.0
        assert tracker.tts_total_characters == 0
    
    def test_stt_cost_calculation(self):
        """Test STT cost calculation."""
        tracker = SpeechCostTracker()
        
        # Record 1 hour of audio
        cost = tracker.record_stt_usage(3600.0)
        
        # Should cost $1.00 per hour
        assert cost == 1.00
        assert tracker.stt_total_seconds == 3600.0
        assert tracker.stt_total_cost == 1.00
        assert len(tracker.usage_records) == 1
    
    def test_tts_cost_calculation(self):
        """Test TTS cost calculation."""
        tracker = SpeechCostTracker()
        
        # Record 1 million characters
        cost = tracker.record_tts_usage(1_000_000)
        
        # Should cost $16.00 per 1M characters
        assert cost == 16.00
        assert tracker.tts_total_characters == 1_000_000
        assert tracker.tts_total_cost == 16.00
        assert len(tracker.usage_records) == 1
    
    def test_budget_alert(self):
        """Test budget alert triggering."""
        tracker = SpeechCostTracker(budget_limit=10.0, alert_threshold=0.8)
        
        assert tracker.budget_alert_sent is False
        
        # Record usage below threshold
        tracker.record_stt_usage(3600.0 * 7)  # $7
        assert tracker.budget_alert_sent is False
        
        # Record usage above threshold
        tracker.record_stt_usage(3600.0 * 2)  # $2 more = $9 total
        assert tracker.budget_alert_sent is True
    
    def test_cost_summary(self):
        """Test cost summary generation."""
        tracker = SpeechCostTracker()
        
        # Record some usage
        tracker.record_stt_usage(3600.0)  # 1 hour = $1
        tracker.record_tts_usage(500_000)  # 500k chars = $8
        
        summary = tracker.get_cost_summary()
        
        assert summary["total_cost"] == 9.00
        assert summary["stt"]["total_hours"] == 1.0
        assert summary["stt"]["total_cost"] == 1.00
        assert summary["tts"]["total_characters"] == 500_000
        assert summary["tts"]["total_cost"] == 8.00
        assert summary["budget_remaining"] == 41.00
    
    def test_global_instance(self):
        """Test global speech cost tracker instance."""
        # Initialize with custom config
        tracker1 = initialize_speech_cost_tracker(budget_limit=100.0)
        assert tracker1.budget_limit == 100.0
        
        # Get global instance
        tracker2 = get_speech_cost_tracker()
        assert tracker1 is tracker2


class TestCostOptimizationIntegration:
    """Test integration of cost optimization components."""
    
    def test_end_to_end_cost_tracking(self):
        """Test end-to-end cost tracking across services."""
        # Initialize optimizers
        llm_optimizer = CostOptimizer(
            enable_caching=True,
            gemini_daily_limit=100,
            azure_budget=50.0
        )
        speech_tracker = SpeechCostTracker(budget_limit=25.0)
        
        # Simulate LLM usage
        llm_optimizer.increment_quota(ServiceType.GEMINI)
        llm_optimizer.record_cost(ServiceType.GEMINI, "generate", 0.0, tokens_used=100)
        
        llm_optimizer.increment_quota(ServiceType.AZURE_OPENAI)
        llm_optimizer.record_cost(ServiceType.AZURE_OPENAI, "generate", 0.05, tokens_used=500)
        
        # Simulate speech usage
        speech_tracker.record_stt_usage(1800.0)  # 30 minutes = $0.50
        speech_tracker.record_tts_usage(100_000)  # 100k chars = $1.60
        
        # Get summaries
        llm_summary = llm_optimizer.get_cost_summary()
        speech_summary = speech_tracker.get_cost_summary()
        
        # Calculate total cost
        total_cost = llm_summary["total_cost"] + speech_summary["total_cost"]
        
        assert llm_summary["total_cost"] == 0.05
        assert speech_summary["total_cost"] == 2.10
        assert total_cost == 2.15
    
    def test_caching_reduces_costs(self):
        """Test that caching reduces API calls and costs."""
        optimizer = CostOptimizer(enable_caching=True)
        
        # First request (cache miss)
        cached = optimizer.get_cached_response(
            ServiceType.GEMINI,
            "generate",
            prompt="test"
        )
        assert cached is None
        
        # Simulate API call and cache response
        response = {"text": "test response"}
        optimizer.cache_response(
            ServiceType.GEMINI,
            "generate",
            response,
            prompt="test"
        )
        optimizer.increment_quota(ServiceType.GEMINI)
        
        # Second request (cache hit - no API call)
        cached = optimizer.get_cached_response(
            ServiceType.GEMINI,
            "generate",
            prompt="test"
        )
        assert cached == response
        
        # Verify only one API call was made
        quota = optimizer.quotas[ServiceType.GEMINI]
        assert quota.current_daily_usage == 1
        assert optimizer.cache_hits == 1
    
    def test_quota_exceeded_triggers_fallback(self):
        """Test that quota exceeded triggers fallback."""
        optimizer = CostOptimizer(gemini_daily_limit=1)
        
        # Use up Gemini quota
        optimizer.increment_quota(ServiceType.GEMINI)
        
        # Check quota (should be exceeded)
        within_quota, reason = optimizer.check_quota(ServiceType.GEMINI)
        assert within_quota is False
        
        # Get fallback service
        fallback = optimizer.get_fallback_service(ServiceType.GEMINI)
        assert fallback == ServiceType.AZURE_OPENAI
        
        # Verify fallback is within quota
        within_quota, reason = optimizer.check_quota(ServiceType.AZURE_OPENAI)
        assert within_quota is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
