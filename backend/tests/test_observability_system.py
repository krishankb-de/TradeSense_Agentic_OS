"""
System tests for observability and monitoring.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
"""

import pytest
import time
from unittest.mock import Mock, patch

from backend.orchestration.telemetry import TelemetryManager, get_telemetry_manager


class TestObservabilitySystem:
    """Test observability system under realistic conditions."""

    def test_trace_completeness_for_all_operations(self):
        """Test that all operations are traced completely."""
        manager = TelemetryManager()

        # Simulate complete pipeline execution
        operations = [
            ("intake_pipeline", "intake", 1200.0),
            ("diagnostic_pipeline", "diagnostic", 3000.0),
            ("fulfillment_pipeline", "fulfillment", 2500.0),
        ]

        for pipeline_name, agent, duration in operations:
            run_id = f"run-{pipeline_name}"

            # Start pipeline
            trace = manager.trace_pipeline_start(
                pipeline_name=pipeline_name,
                run_id=run_id,
                inputs={"test": "input"},
            )

            # Start step
            span = manager.trace_step_start(
                run_id=run_id,
                step_name=f"{agent}_step",
                agent=agent,
                inputs={"step": "input"},
            )

            # Record metrics
            manager.record_agent_response_time(agent, duration)

            # End step
            if span:
                manager.trace_step_end(
                    span_id=span.id if hasattr(span, "id") else f"span-{agent}",
                    status="completed",
                    outputs={"result": "success"},
                )

            # End pipeline
            manager.trace_pipeline_end(
                run_id=run_id,
                status="completed",
                outputs={"final": "result"},
            )

        # Verify all agents were tracked
        summary = manager.get_metrics_summary()
        assert "intake" in summary["agent_response_times"]
        assert "diagnostic" in summary["agent_response_times"]
        assert "fulfillment" in summary["agent_response_times"]

    def test_metrics_accuracy_under_load(self):
        """Test metrics accuracy under load."""
        manager = TelemetryManager()

        # Simulate high load
        expected_latencies = []
        for i in range(1000):
            latency = 400.0 + (i % 100) * 2
            expected_latencies.append(latency)
            manager.record_voice_latency(latency)

        # Calculate expected percentiles
        sorted_latencies = sorted(expected_latencies)
        expected_p50 = sorted_latencies[int(len(sorted_latencies) * 0.50)]
        expected_p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
        expected_p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

        # Get actual percentiles
        percentiles = manager.metrics.get_voice_latency_percentiles()

        # Verify accuracy (within 1% tolerance)
        assert abs(percentiles["p50"] - expected_p50) / expected_p50 < 0.01
        assert abs(percentiles["p95"] - expected_p95) / expected_p95 < 0.01
        assert abs(percentiles["p99"] - expected_p99) / expected_p99 < 0.01

    def test_alert_delivery_and_timing(self):
        """Test alert delivery and timing."""
        manager = TelemetryManager()
        alerts = []

        def alert_handler(alert_type, message, context):
            alerts.append({
                "type": alert_type,
                "message": message,
                "context": context,
                "timestamp": time.time(),
            })

        manager.alerts.add_alert_handler(alert_handler)

        # Trigger voice latency alert
        start = time.time()
        for i in range(100):
            manager.record_voice_latency(650.0)
        alert_time = time.time() - start

        # Verify alert was delivered quickly (< 1 second)
        assert alert_time < 1.0
        assert len(alerts) > 0
        assert alerts[0]["type"] == "voice_latency_high"

    def test_observability_requirements_validation(self):
        """Test that all observability requirements are met."""
        manager = TelemetryManager()

        # Requirement 9.6: Track voice latency (p50, p95, p99)
        manager.record_voice_latency(450.0)
        manager.record_voice_latency(520.0)
        manager.record_voice_latency(380.0)

        percentiles = manager.metrics.get_voice_latency_percentiles()
        assert "p50" in percentiles
        assert "p95" in percentiles
        assert "p99" in percentiles

        # Requirement 9.6: Track agent response time
        manager.record_agent_response_time("intake", 1200.0)
        manager.record_agent_response_time("diagnostic", 3000.0)

        response_times = manager.metrics.get_agent_response_times()
        assert "intake" in response_times
        assert "diagnostic" in response_times

        # Requirement 9.6: Track API costs
        manager.record_api_call("gemini", cost=0.001, success=True)
        manager.record_api_call("azure_openai", cost=0.005, success=True)

        api_costs = manager.metrics.get_api_costs()
        assert "gemini" in api_costs
        assert "azure_openai" in api_costs

        # Requirement 9.7: Track first-time fix rate
        manager.record_job_completion(first_time_fix=True)
        manager.record_job_completion(first_time_fix=False)

        first_time_fix_rate = manager.metrics.get_first_time_fix_rate()
        assert 0.0 <= first_time_fix_rate <= 1.0

        # Requirement 9.8: Track job completion rate
        job_completion_rate = manager.metrics.get_job_completion_rate()
        assert 0.0 <= job_completion_rate <= 1.0

        # Requirement 9.6: Alert on voice latency > 600ms
        alerts = []

        def handler(alert_type, message, context):
            alerts.append(alert_type)

        manager.alerts.add_alert_handler(handler)

        for i in range(100):
            manager.record_voice_latency(650.0)

        assert "voice_latency_high" in alerts

        # Requirement 9.7: Alert on API failure > 1%
        for i in range(100):
            manager.record_api_call("test_api", cost=0.001, success=True)
        for i in range(5):
            manager.record_api_call("test_api", cost=0.0, success=False)

        assert "api_failure_rate_high" in alerts

        # Requirement 9.8: Alert on agent error > 5%
        for i in range(100):
            manager.record_agent_response_time("test_agent", 1200.0)
        for i in range(10):
            manager.record_agent_error("test_agent")

        assert "agent_error_rate_high" in alerts

    def test_distributed_tracing_across_services(self):
        """Test distributed tracing across multiple services."""
        manager = TelemetryManager()

        # Simulate distributed workflow
        run_id = "run-distributed"

        # Service 1: Voice pipeline
        trace = manager.trace_pipeline_start(
            pipeline_name="voice_pipeline",
            run_id=run_id,
            inputs={"audio": "data"},
        )

        span1 = manager.trace_step_start(
            run_id=run_id,
            step_name="stt",
            agent="voice",
            inputs={"audio": "data"},
        )

        manager.record_voice_latency(450.0)

        if span1:
            manager.trace_step_end(
                span_id=span1.id if hasattr(span1, "id") else "span-stt",
                status="completed",
                outputs={"text": "transcription"},
            )

        # Service 2: Agent routing
        span2 = manager.trace_step_start(
            run_id=run_id,
            step_name="routing",
            agent="router",
            inputs={"text": "transcription"},
        )

        if span2:
            manager.trace_step_end(
                span_id=span2.id if hasattr(span2, "id") else "span-routing",
                status="completed",
                outputs={"agent": "intake"},
            )

        # Service 3: Agent execution
        span3 = manager.trace_step_start(
            run_id=run_id,
            step_name="agent_execution",
            agent="intake",
            inputs={"text": "transcription"},
        )

        manager.record_agent_response_time("intake", 1200.0)

        if span3:
            manager.trace_step_end(
                span_id=span3.id if hasattr(span3, "id") else "span-agent",
                status="completed",
                outputs={"result": "lead_created"},
            )

        # End pipeline
        manager.trace_pipeline_end(
            run_id=run_id,
            status="completed",
            outputs={"final": "success"},
        )

        # Verify metrics were collected across services
        summary = manager.get_metrics_summary()
        assert summary["voice_latency"]["p50"] > 0
        assert "intake" in summary["agent_response_times"]

    def test_error_tracking_and_debugging_workflow(self):
        """Test error tracking and debugging workflow."""
        manager = TelemetryManager()

        # Simulate error scenario
        run_id = "run-error"

        trace = manager.trace_pipeline_start(
            pipeline_name="error_pipeline",
            run_id=run_id,
            inputs={"test": "input"},
        )

        span = manager.trace_step_start(
            run_id=run_id,
            step_name="failing_step",
            agent="test_agent",
            inputs={"step": "input"},
        )

        # Simulate error
        try:
            raise ValueError("Test error for debugging")
        except Exception as e:
            manager.capture_error(
                e,
                context={
                    "run_id": run_id,
                    "step": "failing_step",
                    "agent": "test_agent",
                },
            )

            manager.record_agent_error("test_agent")

            if span:
                manager.trace_step_end(
                    span_id=span.id if hasattr(span, "id") else "span-error",
                    status="failed",
                    error=str(e),
                )

        manager.trace_pipeline_end(
            run_id=run_id,
            status="failed",
            error="ValueError: Test error for debugging",
        )

        # Verify error was tracked
        summary = manager.get_metrics_summary()
        assert "test_agent" in summary["agent_error_rates"]
        assert summary["agent_error_rates"]["test_agent"]["error_count"] > 0


class TestObservabilityScalability:
    """Test observability scalability."""

    def test_high_volume_metrics_collection(self):
        """Test metrics collection with high volume."""
        manager = TelemetryManager()

        start = time.time()

        # Collect 100k metrics
        for i in range(100000):
            manager.record_voice_latency(400.0 + (i % 100))

        duration = time.time() - start

        # Verify collection is fast (< 10 seconds for 100k metrics)
        assert duration < 10.0

        # Verify metrics are accurate
        percentiles = manager.metrics.get_voice_latency_percentiles()
        assert percentiles["p50"] > 0
        assert percentiles["p95"] > 0
        assert percentiles["p99"] > 0

    def test_concurrent_pipeline_tracing(self):
        """Test concurrent pipeline tracing."""
        import threading

        manager = TelemetryManager()

        def trace_pipeline(pipeline_id):
            run_id = f"run-{pipeline_id}"

            trace = manager.trace_pipeline_start(
                pipeline_name=f"pipeline_{pipeline_id}",
                run_id=run_id,
                inputs={"test": "input"},
            )

            for i in range(10):
                span = manager.trace_step_start(
                    run_id=run_id,
                    step_name=f"step_{i}",
                    agent="test_agent",
                    inputs={"step": i},
                )

                manager.record_agent_response_time("test_agent", 1000.0 + i * 100)

                if span:
                    manager.trace_step_end(
                        span_id=span.id if hasattr(span, "id") else f"span-{i}",
                        status="completed",
                        outputs={"result": i},
                    )

            manager.trace_pipeline_end(
                run_id=run_id,
                status="completed",
                outputs={"final": "success"},
            )

        # Create 100 concurrent pipelines
        threads = [threading.Thread(target=trace_pipeline, args=(i,)) for i in range(100)]

        start = time.time()

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        duration = time.time() - start

        # Verify tracing is fast (< 30 seconds for 100 pipelines)
        assert duration < 30.0

        # Verify metrics were collected
        summary = manager.get_metrics_summary()
        assert "test_agent" in summary["agent_response_times"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
