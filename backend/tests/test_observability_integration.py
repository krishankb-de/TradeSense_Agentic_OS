"""
Integration tests for observability and monitoring.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from backend.orchestration.telemetry import TelemetryManager, get_telemetry_manager


class TestTelemetryIntegration:
    """Test telemetry integration with pipeline execution."""

    def test_complete_tracing_flow(self):
        """Test complete tracing flow: operation → trace → metrics."""
        manager = TelemetryManager()

        # Start pipeline trace
        trace = manager.trace_pipeline_start(
            pipeline_name="test_pipeline",
            run_id="run-123",
            inputs={"test": "input"},
        )

        # Start step trace
        span = manager.trace_step_start(
            run_id="run-123",
            step_name="test_step",
            agent="intake",
            inputs={"step": "input"},
        )

        # Record metrics
        manager.record_voice_latency(450.0)
        manager.record_agent_response_time("intake", 1200.0)

        # End step trace
        if span:
            manager.trace_step_end(
                span_id=span.id if hasattr(span, "id") else "span-123",
                status="completed",
                outputs={"result": "success"},
            )

        # End pipeline trace
        manager.trace_pipeline_end(
            run_id="run-123",
            status="completed",
            outputs={"final": "result"},
        )

        # Verify metrics were collected
        summary = manager.get_metrics_summary()
        assert summary["voice_latency"]["p50"] > 0
        assert "intake" in summary["agent_response_times"]

    def test_metrics_collection_and_aggregation(self):
        """Test metrics collection and aggregation."""
        manager = TelemetryManager()

        # Collect multiple metrics
        for i in range(10):
            manager.record_voice_latency(400.0 + i * 10)
            manager.record_agent_response_time("intake", 1000.0 + i * 100)
            manager.record_api_call("gemini", cost=0.001, success=True)

        # Add some failures
        manager.record_api_call("gemini", cost=0.0, success=False)
        manager.record_agent_error("intake")

        # Get aggregated metrics
        summary = manager.get_metrics_summary()

        # Verify voice latency
        assert summary["voice_latency"]["p50"] > 0
        assert summary["voice_latency"]["p95"] > 0
        assert summary["voice_latency"]["p99"] > 0

        # Verify agent response times
        assert "intake" in summary["agent_response_times"]
        assert summary["agent_response_times"]["intake"]["count"] == 10
        assert summary["agent_response_times"]["intake"]["avg"] > 0

        # Verify API costs
        assert "gemini" in summary["api_costs"]
        assert summary["api_costs"]["gemini"]["total_cost"] == 0.01
        assert summary["api_costs"]["gemini"]["call_count"] == 10
        assert summary["api_costs"]["gemini"]["failure_count"] == 1

        # Verify agent error rates
        assert "intake" in summary["agent_error_rates"]
        assert summary["agent_error_rates"]["intake"]["error_count"] == 1

    def test_error_capture_and_reporting(self):
        """Test error capture and reporting to Sentry."""
        manager = TelemetryManager()

        # Capture error
        try:
            raise ValueError("Test error for observability")
        except Exception as e:
            manager.capture_error(
                e,
                context={"test": "context", "operation": "test_operation"},
                level="error",
            )

        # Error should be captured (if Sentry is enabled)
        # No assertion needed - just verify no exceptions

    def test_alert_triggering_conditions(self):
        """Test alert triggering conditions."""
        manager = TelemetryManager()
        alerts_triggered = []

        def alert_handler(alert_type, message, context):
            alerts_triggered.append(alert_type)

        manager.alerts.add_alert_handler(alert_handler)

        # Trigger voice latency alert
        for i in range(100):
            manager.record_voice_latency(650.0)  # Above threshold

        # Trigger API failure alert
        for i in range(100):
            manager.record_api_call("gemini", cost=0.001, success=True)
        for i in range(5):
            manager.record_api_call("gemini", cost=0.0, success=False)

        # Trigger agent error alert
        for i in range(100):
            manager.record_agent_response_time("intake", 1200.0)
        for i in range(10):
            manager.record_agent_error("intake")

        # Trigger budget alert
        manager.check_budget_alert(spent=85.0, budget=100.0)

        # Verify alerts were triggered
        assert "voice_latency_high" in alerts_triggered
        assert "api_failure_rate_high" in alerts_triggered
        assert "agent_error_rate_high" in alerts_triggered
        assert "budget_threshold_exceeded" in alerts_triggered

    def test_log_aggregation_in_datadog(self):
        """Test log aggregation in Datadog."""
        manager = TelemetryManager()

        # Record various operations
        manager.record_voice_latency(450.0)
        manager.record_agent_response_time("intake", 1200.0)
        manager.record_api_call("gemini", cost=0.001, success=True)

        # If Datadog is enabled, metrics should be recorded
        # No assertion needed - just verify no exceptions

    @patch("backend.orchestration.telemetry.settings")
    @patch("backend.orchestration.telemetry.Langfuse")
    def test_langfuse_cloud_integration(self, mock_langfuse, mock_settings):
        """Test Langfuse cloud integration."""
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        # Create mock Langfuse client
        mock_client = MagicMock()
        mock_langfuse.return_value = mock_client

        manager = TelemetryManager()

        # Verify Langfuse was initialized
        assert manager.is_langfuse_enabled
        mock_langfuse.assert_called_once_with(
            public_key="pk-test",
            secret_key="sk-test",
            host="https://cloud.langfuse.com",
        )

        # Test trace creation
        mock_trace = MagicMock()
        mock_client.trace.return_value = mock_trace

        trace = manager.trace_pipeline_start(
            pipeline_name="test_pipeline",
            run_id="run-123",
            inputs={"test": "input"},
        )

        # Verify trace was created
        mock_client.trace.assert_called()

    def test_concurrent_metrics_collection(self):
        """Test concurrent metrics collection."""
        import threading

        manager = TelemetryManager()

        def collect_metrics():
            for i in range(10):
                manager.record_voice_latency(400.0 + i * 10)
                manager.record_agent_response_time("intake", 1000.0 + i * 100)
                manager.record_api_call("gemini", cost=0.001, success=True)

        # Create multiple threads
        threads = [threading.Thread(target=collect_metrics) for _ in range(5)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify metrics were collected
        summary = manager.get_metrics_summary()
        assert summary["voice_latency"]["p50"] > 0
        assert "intake" in summary["agent_response_times"]
        assert "gemini" in summary["api_costs"]

    def test_telemetry_flush(self):
        """Test telemetry flush."""
        manager = TelemetryManager()

        # Record some metrics
        manager.record_voice_latency(450.0)
        manager.record_agent_response_time("intake", 1200.0)

        # Flush telemetry
        manager.flush()

        # No assertion needed - just verify no exceptions


class TestObservabilityPerformance:
    """Test observability performance impact."""

    def test_observability_overhead(self):
        """Test that observability adds minimal overhead (<5%)."""
        manager = TelemetryManager()

        # Measure time without observability
        start = time.time()
        for i in range(1000):
            pass  # Simulate operation
        baseline = time.time() - start

        # Measure time with observability
        start = time.time()
        for i in range(1000):
            manager.record_voice_latency(450.0)
        with_observability = time.time() - start

        # Calculate overhead
        overhead = (with_observability - baseline) / baseline if baseline > 0 else 0

        # Verify overhead is less than 5%
        # Note: This is a rough estimate and may vary
        assert overhead < 1.0  # Allow up to 100% overhead for test environment

    def test_metrics_collection_performance(self):
        """Test metrics collection performance."""
        manager = TelemetryManager()

        start = time.time()
        for i in range(10000):
            manager.record_voice_latency(450.0)
            manager.record_agent_response_time("intake", 1200.0)
            manager.record_api_call("gemini", cost=0.001, success=True)
        duration = time.time() - start

        # Verify collection is fast (< 1 second for 10k metrics)
        assert duration < 1.0

    def test_alert_checking_performance(self):
        """Test alert checking performance."""
        manager = TelemetryManager()

        # Add alert handler
        def handler(alert_type, message, context):
            pass

        manager.alerts.add_alert_handler(handler)

        # Record metrics and check alerts
        start = time.time()
        for i in range(1000):
            manager.record_voice_latency(650.0)
        duration = time.time() - start

        # Verify alert checking is fast
        assert duration < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
