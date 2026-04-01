"""
Integration Tests for Cost Optimization API
Tests API endpoints for cost tracking and reporting
"""

import pytest
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.llm.cost_optimizer import initialize_cost_optimizer, ServiceType
from backend.voice.cost_tracker import initialize_speech_cost_tracker


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_cost_tracking():
    """Setup cost tracking for tests."""
    # Initialize with test configuration
    optimizer = initialize_cost_optimizer(
        cache_ttl=3600,
        enable_caching=True,
        gemini_daily_limit=1500,
        azure_budget=100.0,
        azure_alert_threshold=0.8,
    )
    
    speech_tracker = initialize_speech_cost_tracker(
        budget_limit=50.0,
        alert_threshold=0.8,
    )
    
    # Record some test data
    optimizer.record_cost(ServiceType.GEMINI, "generate", 0.0, tokens_used=100)
    optimizer.record_cost(ServiceType.AZURE_OPENAI, "generate", 0.05, tokens_used=500)
    optimizer.increment_quota(ServiceType.GEMINI)
    optimizer.cache_response(ServiceType.GEMINI, "generate", {"text": "test"}, prompt="test")
    
    speech_tracker.record_stt_usage(1800.0)  # 30 minutes
    speech_tracker.record_tts_usage(100_000)  # 100k chars
    
    yield
    
    # Cleanup
    optimizer.clear_cache()


class TestCostOptimizationAPI:
    """Test cost optimization API endpoints."""
    
    def test_get_cost_report(self, client):
        """Test GET /api/cost/report endpoint."""
        response = client.get("/api/cost/report")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "summary" in data
        assert "llm_services" in data
        assert "speech_services" in data
        assert "optimization" in data
        
        assert "total_cost" in data["summary"]
        assert "total_budget" in data["summary"]
        assert "budget_remaining" in data["summary"]
    
    def test_get_cost_projection(self, client):
        """Test GET /api/cost/projection endpoint."""
        response = client.get("/api/cost/projection?days=30")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "projection_period_days" in data
        assert "current_total_cost" in data
        assert "estimated_daily_cost" in data
        assert "projected_cost" in data
        assert "days_until_budget_exhausted" in data
        
        assert data["projection_period_days"] == 30
    
    def test_get_cost_projection_invalid_days(self, client):
        """Test GET /api/cost/projection with invalid days parameter."""
        # Test days < 1
        response = client.get("/api/cost/projection?days=0")
        assert response.status_code == 422
        
        # Test days > 365
        response = client.get("/api/cost/projection?days=400")
        assert response.status_code == 422
    
    def test_get_optimization_recommendations(self, client):
        """Test GET /api/cost/recommendations endpoint."""
        response = client.get("/api/cost/recommendations")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        
        # Check recommendation structure if any exist
        if len(data) > 0:
            rec = data[0]
            assert "category" in rec
            assert "priority" in rec
            assert "description" in rec
            assert "estimated_savings" in rec
            assert "action_items" in rec
    
    def test_get_budget_alerts(self, client):
        """Test GET /api/cost/alerts endpoint."""
        response = client.get("/api/cost/alerts")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "alerts" in data
        assert "count" in data
        assert isinstance(data["alerts"], list)
        assert data["count"] == len(data["alerts"])
    
    def test_get_cost_breakdown(self, client):
        """Test GET /api/cost/breakdown endpoint."""
        response = client.get("/api/cost/breakdown")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have service-level breakdown
        assert isinstance(data, dict)
    
    def test_export_cost_report_json(self, client):
        """Test GET /api/cost/export with JSON format."""
        response = client.get("/api/cost/export?format=json")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "content" in data
        assert "content_type" in data
        assert data["content_type"] == "application/json"
    
    def test_export_cost_report_markdown(self, client):
        """Test GET /api/cost/export with Markdown format."""
        response = client.get("/api/cost/export?format=markdown")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "content" in data
        assert "content_type" in data
        assert data["content_type"] == "text/markdown"
        assert "# Cost Optimization Report" in data["content"]
    
    def test_export_cost_report_invalid_format(self, client):
        """Test GET /api/cost/export with invalid format."""
        response = client.get("/api/cost/export?format=xml")
        
        assert response.status_code == 422
    
    def test_get_cache_stats(self, client):
        """Test GET /api/cost/cache/stats endpoint."""
        response = client.get("/api/cost/cache/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate" in data
        assert "cache_size" in data
    
    def test_clear_cache(self, client):
        """Test POST /api/cost/cache/clear endpoint."""
        # Get initial cache stats
        response = client.get("/api/cost/cache/stats")
        initial_size = response.json()["cache_size"]
        
        # Clear cache
        response = client.post("/api/cost/cache/clear")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        
        # Verify cache is cleared
        response = client.get("/api/cost/cache/stats")
        new_size = response.json()["cache_size"]
        assert new_size == 0
    
    def test_get_quota_status(self, client):
        """Test GET /api/cost/quota/status endpoint."""
        response = client.get("/api/cost/quota/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have quota info for services
        assert "gemini" in data
        assert "azure_openai" in data
        
        # Check structure
        gemini_quota = data["gemini"]
        assert "daily_usage" in gemini_quota
        assert "daily_limit" in gemini_quota
        assert "daily_remaining" in gemini_quota
    
    def test_get_budget_status(self, client):
        """Test GET /api/cost/budget/status endpoint."""
        response = client.get("/api/cost/budget/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have budget info for services
        assert "azure_openai" in data
        
        # Check structure
        azure_budget = data["azure_openai"]
        assert "current_spend" in azure_budget
        assert "budget_limit" in azure_budget
        assert "budget_remaining" in azure_budget
        assert "budget_used_pct" in azure_budget
    
    def test_reset_budget_alerts(self, client):
        """Test POST /api/cost/budget/reset-alerts endpoint."""
        response = client.post("/api/cost/budget/reset-alerts")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_get_speech_cost_summary(self, client):
        """Test GET /api/cost/speech/summary endpoint."""
        response = client.get("/api/cost/speech/summary")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "total_cost" in data
        assert "stt" in data
        assert "tts" in data
        assert "budget_limit" in data
        
        # Check STT structure
        assert "total_seconds" in data["stt"]
        assert "total_cost" in data["stt"]
        
        # Check TTS structure
        assert "total_characters" in data["tts"]
        assert "total_cost" in data["tts"]


class TestCostOptimizationIntegration:
    """Test integration scenarios."""
    
    def test_end_to_end_cost_tracking_flow(self, client):
        """Test complete cost tracking workflow."""
        # 1. Get initial report
        response = client.get("/api/cost/report")
        assert response.status_code == 200
        initial_report = response.json()
        initial_cost = initial_report["summary"]["total_cost"]
        
        # 2. Check quota status
        response = client.get("/api/cost/quota/status")
        assert response.status_code == 200
        
        # 3. Check budget status
        response = client.get("/api/cost/budget/status")
        assert response.status_code == 200
        
        # 4. Get recommendations
        response = client.get("/api/cost/recommendations")
        assert response.status_code == 200
        
        # 5. Get projection
        response = client.get("/api/cost/projection?days=30")
        assert response.status_code == 200
        projection = response.json()
        assert projection["current_total_cost"] == initial_cost
        
        # 6. Export report
        response = client.get("/api/cost/export?format=markdown")
        assert response.status_code == 200
    
    def test_cache_effectiveness(self, client):
        """Test cache effectiveness tracking."""
        # Get initial cache stats
        response = client.get("/api/cost/cache/stats")
        initial_stats = response.json()
        
        # Clear cache
        response = client.post("/api/cost/cache/clear")
        assert response.status_code == 200
        
        # Verify cache cleared
        response = client.get("/api/cost/cache/stats")
        cleared_stats = response.json()
        assert cleared_stats["cache_size"] == 0
    
    def test_budget_alert_workflow(self, client):
        """Test budget alert workflow."""
        # Get alerts
        response = client.get("/api/cost/alerts")
        assert response.status_code == 200
        
        # Reset alerts
        response = client.post("/api/cost/budget/reset-alerts")
        assert response.status_code == 200
        
        # Verify alerts reset
        response = client.get("/api/cost/budget/status")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
