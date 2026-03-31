"""
Unit tests for observability and monitoring.

**Validates: Requirements 9.1, 9.2, 9.4, 9.5, 9.6, 9.7, 9.8**
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from backend.orchestration.telemetry import (
    MetricsCollector,
    AlertManager,
    TelemetryManager,
    get_telemetry_manager,
)


class TestMetricsCollector:
    """Test metrics collection functionality."""

    def test_record_voice_latency(self):
        """Test recording voice latency."""
        collector = MetricsCollector()

        collector.record_voice_latency(450.0)
        collector.record_voice_latency(520.0)
        collector.record_voice_latency(380.0)

        percentiles = collector.get_voice_latency_percentiles()
        assert percentiles["p50"] > 0
        assert percentiles["p95"] > 0
        assert percentiles["p99"] > 0

    def test_voice_latency_percentiles_empty(self):
        """Test voice latency percentiles with no data."""
        collector = MetricsCollector()

        percentiles = collector.get_voice_latency_percentiles()
        assert percentiles["p50"] == 0.0
        assert percentiles["p95"] == 0.0
        assert percentiles["p99"] == 0.0

    def test_record_agent_response_time(self):
        """Test recording agent response times."""
        collector = MetricsCollector()

        collector.record_agent_response_time("intake", 1200.0)
        collector.record_agent_response_time("intake", 1500.0)
        collector.record_agent_response_time("diagnostic", 3000.0)

        response_times = collector.get_agent_response_times()
        assert "intake" in response_times
        assert "diagnostic" in response_times
        assert response_times["intake"]["count"] == 2
        assert response_times["diagnostic"]["count"] == 1
        assert response_times["intake"]["avg"] == 1350.0

    def test_record_api_cost(self):
        """Test recording API costs."""
        collector = MetricsCollector()

        collector.record_api_cost("gemini", 0.001)
        collector.record_api_cost("gemini", 0.002)
        collector.record_api_cost("azure_openai", 0.005)

        api_costs = collector.get_api_costs()
        assert "gemini" in api_costs
        assert "azure_openai" in api_costs
        assert api_costs["gemini"]["total_cost"] == 0.003
        assert api_costs["gemini"]["call_count"] == 2
        assert api_costs["azure_openai"]["total_cost"] == 0.005

    def test_record_api_failure(self):
        """Test recording API failures."""
        collector = MetricsCollector()

        # Record successful calls
        collector.record_api_cost("gemini", 0.001)
        collector.record_api_cost("gemini", 0.001)

        # Record failures
        collector.record_api_failure("gemini")

        api_costs = collector.get_api_costs()
        assert api_costs["gemini"]["failure_count"] == 1
        assert api_costs["gemini"]["failure_rate"] == 1 / 2

    def test_record_agent_error(self):
        """Test recording agent errors."""
        collector = MetricsCollector()

        # Record successful calls
        collector.record_agent_response_time("intake", 1200.0)
        collector.record_agent_response_time("intake", 1300.0)

        # Record error
        collector.record_agent_error("intake")

        error_rates = collector.get_agent_error_rates()
        assert "intake" in error_rates
        assert error_rates["intake"]["error_count"] == 1
        assert error_rates["intake"]["total_calls"] == 2
        assert error_rates["intake"]["error_rate"] == 0.5

    def test_record_job_completion(self):
        """Test recording job completions."""
        collector = MetricsCollector()

        collector.record_job_completion(first_time_fix=True)
        collector.record_job_completion(first_time_fix=True)
        collector.record_job_completion(first_time_fix=False)

        assert collector.get_first_time_fix_rate() == 2 / 3
        assert collector.get_job_completion_rate() == 1.0

    def test_reset_metrics(self):
        """Test resetting all metrics."""
        collector = MetricsCollector()

        collector.record_voice_latency(450.0)
        collector.record_agent_response_time("intake", 1200.0)
        collector.record_api_cost("gemini", 0.001)
        collector.record_job_completion(first_time_fix=True)

        collector.reset()

        assert collector.get_voice_latency_percentiles()["p50"] == 0.0
        assert len(collector.get_agent_response_times()) == 0
        assert len(collector.get_api_costs()) == 0
        assert collector.get_first_time_fix_rate() == 0.0


class TestAlertManager:
    """Test alerting functionality."""

    def test_voice_latency_alert(self):
        """Test voice latency alert triggering."""
        manager = AlertManager()
        alert_triggered = False

        def handler(alert_type, message, context):
            nonlocal alert_triggered
            alert_triggered = True
            assert alert_type == "voice_latency_high"
            assert context["p95_latency"] > 600.0

        manager.add_alert_handler(handler)
        manager.check_voice_latency(650.0)

        assert alert_triggered

    def test_voice_latency_no_alert(self):
        """Test voice latency below threshold."""
        manager = AlertManager()
        alert_triggered = False

        def handler(alert_type, message, context):
            nonlocal alert_triggered
            alert_triggered = True

        manager.add_alert_handler(handler)
        manager.check_voice_latency(500.0)

        assert not alert_triggered

    def test_api_failure_rate_alert(self):
        """Test API failure rate alert triggering."""
        manager = AlertManager()
        alert_triggered = False

        def handler(alert_type, message, context):
            nonlocal alert_triggered
            alert_triggered = True
            assert alert_type == "api_failure_rate_high"
            assert context["provider"] == "gemini"
            assert context["failure_rate"] > 0.01

        manager.add_alert_handler(handler)
        manager.check_api_failure_rate("gemini", 0.05)

        assert alert_triggered

    def test_agent_error_rate_alert(self):
        """Test agent error rate alert triggering."""
        manager = AlertManager()
        alert_triggered = False

        def handler(alert_type, message, context):
            nonlocal alert_triggered
            alert_triggered = True
            assert alert_type == "agent_error_rate_high"
            assert context["agent"] == "intake"
            assert context["error_rate"] > 0.05

        manager.add_alert_handler(handler)
        manager.check_agent_error_rate("intake", 0.10)

        assert alert_triggered

    def test_budget_alert(self):
        """Test budget alert triggering."""
        manager = AlertManager()
        alert_triggered = False

        def handler(alert_type, message, context):
            nonlocal alert_triggered
            alert_triggered = True
            assert alert_type == "budget_threshold_exceeded"
            assert context["spent"] == 85.0
            assert context["budget"] == 100.0

        manager.add_alert_handler(handler)
        manager.check_budget(spent=85.0, budget=100.0)

        assert alert_triggered

    def test_multiple_alert_handlers(self):
        """Test multiple alert handlers."""
        manager = AlertManager()
        handler1_called = False
        handler2_called = False

        def handler1(alert_type, message, context):
            nonlocal handler1_called
            handler1_called = True

        def handler2(alert_type, message, context):
            nonlocal handler2_called
            handler2_called = True

        manager.add_alert_handler(handler1)
        manager.add_alert_handler(handler2)
        manager.check_voice_latency(650.0)

        assert handler1_called
        assert handler2_called


class TestTelemetryManager:
    """Test telemetry manager functionality."""

    @patch("backend.orchestration.telemetry.settings")
    def test_initialization_without_credentials(self, mock_settings):
        """Test initialization without credentials."""
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        manager = TelemetryManager()

        assert not manager.is_langfuse_enabled
        assert not manager.is_datadog_enabled
        assert not manager.is_sentry_enabled
        assert not manager.is_phoenix_enabled

    @patch("backend.orchestration.telemetry.settings")
    def test_langfuse_initialization(self, mock_settings):
        """Test Langfuse initialization."""
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        with patch("langfuse.Langfuse") as mock_langfuse:
            manager = TelemetryManager()

            assert manager.is_langfuse_enabled
            mock_langfuse.assert_called_once()

    def test_record_voice_latency(self):
        """Test recording voice latency."""
        manager = TelemetryManager()

        manager.record_voice_latency(450.0)
        manager.record_voice_latency(520.0)

        summary = manager.get_metrics_summary()
        assert summary["voice_latency"]["p50"] > 0

    def test_record_agent_response_time(self):
        """Test recording agent response time."""
        manager = TelemetryManager()

        manager.record_agent_response_time("intake", 1200.0)
        manager.record_agent_response_time("diagnostic", 3000.0)

        summary = manager.get_metrics_summary()
        assert "intake" in summary["agent_response_times"]
        assert "diagnostic" in summary["agent_response_times"]

    def test_record_api_call(self):
        """Test recording API calls."""
        manager = TelemetryManager()

        manager.record_api_call("gemini", cost=0.001, success=True)
        manager.record_api_call("gemini", cost=0.002, success=True)
        manager.record_api_call("gemini", cost=0.0, success=False)

        summary = manager.get_metrics_summary()
        assert "gemini" in summary["api_costs"]
        assert summary["api_costs"]["gemini"]["total_cost"] == 0.003
        assert summary["api_costs"]["gemini"]["failure_count"] == 1

    def test_record_agent_error(self):
        """Test recording agent errors."""
        manager = TelemetryManager()

        manager.record_agent_response_time("intake", 1200.0)
        manager.record_agent_error("intake")

        summary = manager.get_metrics_summary()
        assert "intake" in summary["agent_error_rates"]
        assert summary["agent_error_rates"]["intake"]["error_count"] == 1

    def test_record_job_completion(self):
        """Test recording job completions."""
        manager = TelemetryManager()

        manager.record_job_completion(first_time_fix=True)
        manager.record_job_completion(first_time_fix=False)

        summary = manager.get_metrics_summary()
        assert summary["first_time_fix_rate"] == 0.5
        assert summary["job_completion_rate"] == 1.0

    def test_get_metrics_summary(self):
        """Test getting metrics summary."""
        manager = TelemetryManager()

        manager.record_voice_latency(450.0)
        manager.record_agent_response_time("intake", 1200.0)
        manager.record_api_call("gemini", cost=0.001, success=True)
        manager.record_job_completion(first_time_fix=True)

        summary = manager.get_metrics_summary()

        assert "voice_latency" in summary
        assert "agent_response_times" in summary
        assert "api_costs" in summary
        assert "agent_error_rates" in summary
        assert "first_time_fix_rate" in summary
        assert "job_completion_rate" in summary

    def test_get_telemetry_manager_singleton(self):
        """Test telemetry manager singleton."""
        manager1 = get_telemetry_manager()
        manager2 = get_telemetry_manager()

        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
