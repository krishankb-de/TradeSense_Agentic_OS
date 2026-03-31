"""
End-to-end tests for observability and monitoring.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8**
"""

import pytest
import time
from unittest.mock import Mock, patch

from backend.orchestration.telemetry import TelemetryManager, get_telemetry_manager


class TestObservabilityEndToEnd:
    """Test complete observable workflows."""

    def test_complete_observable_workflow(self):
        """Test complete workflow: operation → traces → metrics → alerts."""
        manager = TelemetryManager()
        alerts = []

        def alert_handler(alert_type, message, context):
            alerts.append({
                "type": alert_type,
                "message": message,
                "context": context,
            })

        manager.alerts.add_alert_handler(alert_handler)

        # Simulate complete workflow
        run_id = "run-e2e"

        # 1. Start pipeline
        trace = manager.trace_pipeline_start(
            pipeline_name="intake_pipeline",
            run_id=run_id,
            inputs={"customer": "John Doe", "issue": "AC not working"},
        )

        # 2. Voice processing
        span_voice = manager.trace_step_start(
            run_id=run_id,
            step_name="voice_processing",
            agent="voice",
            inputs={"audio": "data"},
        )

        manager.record_voice_latency(450.0)

        if span_voice:
            manager.trace_step_end(
                span_id=span_voice.id if hasattr(span_voice, "id") else "span-voice",
                status="completed",
                outputs={"text": "My AC is not working"},
            )

        # 3. Intent classification
        span_intent = manager.trace_step_start(
            run_id=run_id,
            step_name="intent_classification",
            agent="router",
            inputs={"text": "My AC is not working"},
        )

        manager.record_api_call("gemini", cost=0.001, success=True)

        if span_intent:
            manager.trace_step_end(
                span_id=span_intent.id if hasattr(span_intent, "id") else "span-intent",
                status="completed",
                outputs={"intent": "lead_intake", "confidence": 0.95},
            )

        # 4. Agent execution
        span_agent = manager.trace_step_start(
            run_id=run_id,
            step_name="agent_execution",
            agent="intake",
            inputs={"intent": "lead_intake", "text": "My AC is not working"},
        )

        manager.record_agent_response_time("intake", 1200.0)
        manager.record_api_call("gemini", cost=0.002, success=True)

        if span_agent:
            manager.trace_step_end(
                span_id=span_agent.id if hasattr(span_agent, "id") else "span-agent",
                status="completed",
                outputs={"lead_id": "lead-123", "urgency": "urgent"},
            )

        # 5. Job completion
        manager.record_job_completion(first_time_fix=True)

        # 6. End pipeline
        manager.trace_pipeline_end(
            run_id=run_id,
            status="completed",
            outputs={"lead_id": "lead-123", "status": "scheduled"},
        )

        # Verify complete workflow was tracked
        summary = manager.get_metrics_summary()

        # Verify voice latency
        assert summary["voice_latency"]["p50"] > 0

        # Verify agent response times
        assert "intake" in summary["agent_response_times"]

        # Verify API costs
        assert "gemini" in summary["api_costs"]
        assert summary["api_costs"]["gemini"]["total_cost"] == 0.003

        # Verify job metrics
        assert summary["first_time_fix_rate"] == 1.0
        assert summary["job_completion_rate"] == 1.0

    def test_multi_agent_workflow_with_handoffs(self):
        """Test multi-agent workflow with handoffs."""
        manager = TelemetryManager()

        run_id = "run-multi-agent"

        # Start pipeline
        trace = manager.trace_pipeline_start(
            pipeline_name="multi_agent_pipeline",
            run_id=run_id,
            inputs={"customer": "Jane Smith", "issue": "Equipment diagnosis needed"},
        )

        # Agent 1: Intake
        span_intake = manager.trace_step_start(
            run_id=run_id,
            step_name="intake",
            agent="intake",
            inputs={"issue": "Equipment diagnosis needed"},
        )

        manager.record_agent_response_time("intake", 1200.0)
        manager.record_api_call("gemini", cost=0.001, success=True)

        if span_intake:
            manager.trace_step_end(
                span_id=span_intake.id if hasattr(span_intake, "id") else "span-intake",
                status="completed",
                outputs={"lead_id": "lead-456", "next_agent": "diagnostic"},
            )

        # Agent 2: Diagnostic
        span_diagnostic = manager.trace_step_start(
            run_id=run_id,
            step_name="diagnostic",
            agent="diagnostic",
            inputs={"lead_id": "lead-456", "equipment_image": "image_data"},
        )

        manager.record_agent_response_time("diagnostic", 3000.0)
        manager.record_api_call("gemini", cost=0.005, success=True)

        if span_diagnostic:
            manager.trace_step_end(
                span_id=span_diagnostic.id if hasattr(span_diagnostic, "id") else "span-diagnostic",
                status="completed",
                outputs={"diagnosis": "Faulty capacitor", "parts": ["CAP-123"]},
            )

        # Agent 3: Fulfillment
        span_fulfillment = manager.trace_step_start(
            run_id=run_id,
            step_name="fulfillment",
            agent="fulfillment",
            inputs={"diagnosis": "Faulty capacitor", "parts": ["CAP-123"]},
        )

        manager.record_agent_response_time("fulfillment", 2500.0)
        manager.record_api_call("gemini", cost=0.002, success=True)

        if span_fulfillment:
            manager.trace_step_end(
                span_id=span_fulfillment.id if hasattr(span_fulfillment, "id") else "span-fulfillment",
                status="completed",
                outputs={"job_id": "job-789", "scheduled": "2024-01-15 10:00"},
            )

        # End pipeline
        manager.trace_pipeline_end(
            run_id=run_id,
            status="completed",
            outputs={"job_id": "job-789", "status": "scheduled"},
        )

        # Verify all agents were tracked
        summary = manager.get_metrics_summary()
        assert "intake" in summary["agent_response_times"]
        assert "diagnostic" in summary["agent_response_times"]
        assert "fulfillment" in summary["agent_response_times"]

        # Verify API costs
        assert summary["api_costs"]["gemini"]["total_cost"] == 0.008

    def test_error_recovery_and_graceful_degradation(self):
        """Test error recovery and graceful degradation."""
        manager = TelemetryManager()

        run_id = "run-error-recovery"

        # Start pipeline
        trace = manager.trace_pipeline_start(
            pipeline_name="error_recovery_pipeline",
            run_id=run_id,
            inputs={"test": "input"},
        )

        # Step 1: Success
        span1 = manager.trace_step_start(
            run_id=run_id,
            step_name="step1",
            agent="test_agent",
            inputs={"step": 1},
        )

        manager.record_agent_response_time("test_agent", 1000.0)

        if span1:
            manager.trace_step_end(
                span_id=span1.id if hasattr(span1, "id") else "span-1",
                status="completed",
                outputs={"result": "success"},
            )

        # Step 2: Failure
        span2 = manager.trace_step_start(
            run_id=run_id,
            step_name="step2",
            agent="test_agent",
            inputs={"step": 2},
            attempt=1,
        )

        try:
            raise ValueError("Simulated error")
        except Exception as e:
            manager.capture_error(e, context={"run_id": run_id, "step": "step2"})
            manager.record_agent_error("test_agent")

            if span2:
                manager.trace_step_end(
                    span_id=span2.id if hasattr(span2, "id") else "span-2",
                    status="failed",
                    error=str(e),
                )

        # Step 2: Retry (Success)
        span2_retry = manager.trace_step_start(
            run_id=run_id,
            step_name="step2",
            agent="test_agent",
            inputs={"step": 2},
            attempt=2,
        )

        manager.record_agent_response_time("test_agent", 1200.0)

        if span2_retry:
            manager.trace_step_end(
                span_id=span2_retry.id if hasattr(span2_retry, "id") else "span-2-retry",
                status="completed",
                outputs={"result": "success_after_retry"},
            )

        # End pipeline
        manager.trace_pipeline_end(
            run_id=run_id,
            status="completed",
            outputs={"final": "success_with_retry"},
        )

        # Verify error was tracked
        summary = manager.get_metrics_summary()
        assert "test_agent" in summary["agent_error_rates"]
        assert summary["agent_error_rates"]["test_agent"]["error_count"] == 1

    def test_data_persistence_from_observable_operations(self):
        """Test data persistence from observable operations."""
        manager = TelemetryManager()

        # Collect metrics over time
        for i in range(100):
            manager.record_voice_latency(400.0 + i)
            manager.record_agent_response_time("intake", 1000.0 + i * 10)
            manager.record_api_call("gemini", cost=0.001, success=True)

        # Get initial summary
        summary1 = manager.get_metrics_summary()

        # Collect more metrics
        for i in range(100):
            manager.record_voice_latency(500.0 + i)
            manager.record_agent_response_time("diagnostic", 2000.0 + i * 20)
            manager.record_api_call("azure_openai", cost=0.005, success=True)

        # Get updated summary
        summary2 = manager.get_metrics_summary()

        # Verify data persistence
        assert summary2["voice_latency"]["p50"] > summary1["voice_latency"]["p50"]
        assert "diagnostic" in summary2["agent_response_times"]
        assert "azure_openai" in summary2["api_costs"]

    def test_complete_job_lifecycle_with_observability(self):
        """Test complete job lifecycle with observability."""
        manager = TelemetryManager()

        # Job 1: First-time fix
        run_id_1 = "run-job-1"

        trace1 = manager.trace_pipeline_start(
            pipeline_name="job_lifecycle",
            run_id=run_id_1,
            inputs={"job_id": "job-1"},
        )

        manager.record_voice_latency(420.0)
        manager.record_agent_response_time("intake", 1100.0)
        manager.record_agent_response_time("diagnostic", 2800.0)
        manager.record_agent_response_time("fulfillment", 2300.0)
        manager.record_api_call("gemini", cost=0.008, success=True)
        manager.record_job_completion(first_time_fix=True)

        manager.trace_pipeline_end(
            run_id=run_id_1,
            status="completed",
            outputs={"job_id": "job-1", "status": "completed", "first_time_fix": True},
        )

        # Job 2: Requires follow-up
        run_id_2 = "run-job-2"

        trace2 = manager.trace_pipeline_start(
            pipeline_name="job_lifecycle",
            run_id=run_id_2,
            inputs={"job_id": "job-2"},
        )

        manager.record_voice_latency(480.0)
        manager.record_agent_response_time("intake", 1250.0)
        manager.record_agent_response_time("diagnostic", 3200.0)
        manager.record_agent_response_time("fulfillment", 2600.0)
        manager.record_api_call("gemini", cost=0.010, success=True)
        manager.record_job_completion(first_time_fix=False)

        manager.trace_pipeline_end(
            run_id=run_id_2,
            status="completed",
            outputs={"job_id": "job-2", "status": "completed", "first_time_fix": False},
        )

        # Verify job metrics
        summary = manager.get_metrics_summary()
        assert summary["first_time_fix_rate"] == 0.5
        assert summary["job_completion_rate"] == 1.0

        # Verify all agents were tracked
        assert "intake" in summary["agent_response_times"]
        assert "diagnostic" in summary["agent_response_times"]
        assert "fulfillment" in summary["agent_response_times"]

        # Verify API costs
        assert summary["api_costs"]["gemini"]["total_cost"] == 0.018


class TestObservabilityRealWorld:
    """Test observability with real-world scenarios."""

    def test_high_latency_scenario(self):
        """Test observability during high latency scenario."""
        manager = TelemetryManager()
        alerts = []

        def alert_handler(alert_type, message, context):
            alerts.append(alert_type)

        manager.alerts.add_alert_handler(alert_handler)

        # Simulate high latency
        for i in range(100):
            manager.record_voice_latency(700.0)  # Above threshold

        # Verify alert was triggered
        assert "voice_latency_high" in alerts

        # Verify metrics
        summary = manager.get_metrics_summary()
        assert summary["voice_latency"]["p95"] > 600.0

    def test_api_failure_scenario(self):
        """Test observability during API failure scenario."""
        manager = TelemetryManager()
        alerts = []

        def alert_handler(alert_type, message, context):
            alerts.append(alert_type)

        manager.alerts.add_alert_handler(alert_handler)

        # Simulate API failures
        for i in range(90):
            manager.record_api_call("gemini", cost=0.001, success=True)
        for i in range(10):
            manager.record_api_call("gemini", cost=0.0, success=False)

        # Verify alert was triggered
        assert "api_failure_rate_high" in alerts

        # Verify metrics
        summary = manager.get_metrics_summary()
        assert summary["api_costs"]["gemini"]["failure_rate"] > 0.01

    def test_agent_error_scenario(self):
        """Test observability during agent error scenario."""
        manager = TelemetryManager()
        alerts = []

        def alert_handler(alert_type, message, context):
            alerts.append(alert_type)

        manager.alerts.add_alert_handler(alert_handler)

        # Simulate agent errors
        for i in range(90):
            manager.record_agent_response_time("intake", 1200.0)
        for i in range(10):
            manager.record_agent_error("intake")

        # Verify alert was triggered
        assert "agent_error_rate_high" in alerts

        # Verify metrics
        summary = manager.get_metrics_summary()
        assert summary["agent_error_rates"]["intake"]["error_rate"] > 0.05


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
