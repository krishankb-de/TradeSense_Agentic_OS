"""
Integration tests for telemetry with pipeline orchestration.

**Validates: Requirements 3.8, 9.1, 9.2, 9.3**
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch

from backend.orchestration.pipeline import (
    Pipeline,
    PipelineExecutor,
    PipelineStep,
    RetryPolicy,
)


@pytest.mark.asyncio
class TestTelemetryIntegration:
    """Test telemetry integration with pipeline execution."""

    async def test_pipeline_execution_with_telemetry(self):
        """Test that telemetry is emitted during pipeline execution."""
        # Mock telemetry manager
        with patch("backend.orchestration.pipeline.get_telemetry_manager") as mock_get_telemetry:
            mock_telemetry = MagicMock()
            mock_get_telemetry.return_value = mock_telemetry

            # Create a simple pipeline
            async def step_function(input_data):
                return {"output": f"processed_{input_data}"}

            pipeline = Pipeline(name="test_pipeline")
            step = PipelineStep(
                name="process_step",
                agent="test_agent",
                function=step_function,
                inputs=["input_data"],
                outputs=["output"],
            )
            pipeline.add_step(step)

            # Execute pipeline
            executor = PipelineExecutor()
            run = await executor.execute(pipeline, {"input_data": "test"})

            # Verify telemetry was called
            assert run.status.value == "completed"
            
            # Verify pipeline trace was started
            mock_telemetry.trace_pipeline_start.assert_called_once()
            call_args = mock_telemetry.trace_pipeline_start.call_args
            assert call_args[1]["pipeline_name"] == "test_pipeline"
            assert call_args[1]["run_id"] == run.id
            
            # Verify pipeline trace was ended
            mock_telemetry.trace_pipeline_end.assert_called_once()
            end_call_args = mock_telemetry.trace_pipeline_end.call_args
            assert end_call_args[1]["run_id"] == run.id
            assert end_call_args[1]["status"] == "completed"
            
            # Verify step trace was started
            mock_telemetry.trace_step_start.assert_called_once()
            step_call_args = mock_telemetry.trace_step_start.call_args
            assert step_call_args[1]["step_name"] == "process_step"
            assert step_call_args[1]["agent"] == "test_agent"
            
            # Verify metrics were recorded
            assert mock_telemetry.record_metric.call_count >= 1

    async def test_pipeline_failure_with_telemetry(self):
        """Test that telemetry captures errors during pipeline execution."""
        # Mock telemetry manager
        with patch("backend.orchestration.pipeline.get_telemetry_manager") as mock_get_telemetry:
            mock_telemetry = MagicMock()
            mock_get_telemetry.return_value = mock_telemetry

            # Create a pipeline with a failing step
            async def failing_step():
                raise ValueError("Test error")

            pipeline = Pipeline(name="failing_pipeline")
            step = PipelineStep(
                name="failing_step",
                agent="test_agent",
                function=failing_step,
                retry_policy=RetryPolicy(max_retries=0),  # No retries
            )
            pipeline.add_step(step)

            # Execute pipeline and expect failure
            executor = PipelineExecutor()
            with pytest.raises(RuntimeError):
                await executor.execute(pipeline, {})

            # Verify error was captured
            mock_telemetry.capture_error.assert_called()
            error_call_args = mock_telemetry.capture_error.call_args
            assert isinstance(error_call_args[0][0], ValueError)
            
            # Verify pipeline trace ended with error
            mock_telemetry.trace_pipeline_end.assert_called_once()
            end_call_args = mock_telemetry.trace_pipeline_end.call_args
            assert end_call_args[1]["status"] == "failed"
            assert "error" in end_call_args[1]

    async def test_step_retry_with_telemetry(self):
        """Test that telemetry tracks retry attempts."""
        # Mock telemetry manager
        with patch("backend.orchestration.pipeline.get_telemetry_manager") as mock_get_telemetry:
            mock_telemetry = MagicMock()
            mock_get_telemetry.return_value = mock_telemetry

            # Create a step that fails once then succeeds
            call_count = 0

            async def flaky_step():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise ValueError("First attempt fails")
                return {"result": "success"}

            pipeline = Pipeline(name="retry_pipeline")
            step = PipelineStep(
                name="flaky_step",
                agent="test_agent",
                function=flaky_step,
                retry_policy=RetryPolicy(max_retries=2, initial_delay=0.1),
            )
            pipeline.add_step(step)

            # Execute pipeline
            executor = PipelineExecutor()
            run = await executor.execute(pipeline, {})

            # Verify pipeline completed
            assert run.status.value == "completed"
            
            # Verify step trace was started twice (initial + retry)
            assert mock_telemetry.trace_step_start.call_count == 2
            
            # Verify error was captured for the first attempt
            mock_telemetry.capture_error.assert_called()
            
            # Verify final step trace ended successfully
            assert mock_telemetry.trace_step_end.call_count >= 1


def test_telemetry_graceful_degradation():
    """Test that pipeline works even if telemetry is unavailable."""
    # Mock telemetry manager to have no services enabled
    with patch("backend.orchestration.telemetry.settings") as mock_settings:
        mock_settings.langfuse_public_key = ""
        mock_settings.langfuse_secret_key = ""
        mock_settings.use_datadog = False
        mock_settings.sentry_dsn = ""
        mock_settings.phoenix_collector_endpoint = ""

        # Create a simple pipeline
        async def step_function():
            return {"result": "success"}

        pipeline = Pipeline(name="test_pipeline")
        step = PipelineStep(
            name="test_step",
            agent="test_agent",
            function=step_function,
        )
        pipeline.add_step(step)

        # Execute pipeline - should work fine without telemetry
        executor = PipelineExecutor()
        
        async def run_test():
            run = await executor.execute(pipeline, {})
            assert run.status.value == "completed"
        
        asyncio.run(run_test())
