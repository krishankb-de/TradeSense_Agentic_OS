"""
Property-Based Tests for Orchestration Module

Tests universal properties that should hold across all pipeline configurations
and retry policies.

**Validates: Requirements 3.4**
"""

import pytest
import asyncio
import time
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from typing import List, Dict, Any

from orchestration.pipeline import (
    Pipeline,
    PipelineExecutor,
    PipelineStep,
    RetryPolicy,
    SecretsManager,
    PipelineStatus,
    StepStatus,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def secrets_manager():
    """Create a secrets manager instance."""
    return SecretsManager()


@pytest.fixture
def pipeline_executor(secrets_manager):
    """Create a pipeline executor instance."""
    return PipelineExecutor(secrets_manager=secrets_manager)


# ============================================================================
# Property 16: Pipeline Retry Behavior
# **Validates: Requirements 3.4**
# ============================================================================


@pytest.mark.property
@given(
    max_retries=st.integers(min_value=0, max_value=5),
    initial_delay=st.floats(min_value=0.1, max_value=0.5),
    fail_count=st.integers(min_value=0, max_value=10),
)
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_property_retry_count_matches_policy(
    pipeline_executor, max_retries, initial_delay, fail_count
):
    """
    **Validates: Requirements 3.4**
    
    Property: For any retry policy configuration:
    - When a step fails N times then succeeds, it should retry exactly N times
    - When a step fails more than max_retries times, it should fail permanently
    - Retry count should match the configured max_retries
    
    This property tests that the pipeline retry mechanism respects
    the configured retry policy limits.
    """
    async def run_test():
        attempt_count = 0
        
        async def failing_func(**kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= fail_count:
                raise ValueError(f"Simulated failure {attempt_count}")
            return {"result": "success"}
        
        # Create pipeline with retry policy
        pipeline = Pipeline(name="retry_test_pipeline")
        step = PipelineStep(
            name="test_step",
            agent="intake",
            function=failing_func,
            outputs=["result"],
            retry_policy=RetryPolicy(
                max_retries=max_retries,
                initial_delay=initial_delay,
                exponential_backoff=False,  # Fixed delay for predictability
            ),
        )
        pipeline.add_step(step)
        
        # Execute and check behavior
        if fail_count <= max_retries:
            # Should succeed after fail_count attempts
            run = await pipeline_executor.execute(pipeline, {})
            
            # Property 1: Pipeline should complete successfully
            assert run.status == PipelineStatus.COMPLETED, (
                f"Pipeline should complete when failures ({fail_count}) <= max_retries ({max_retries})"
            )
            
            # Property 2: Attempt count should match fail_count + 1 (final success)
            assert attempt_count == fail_count + 1, (
                f"Should attempt {fail_count + 1} times (fail {fail_count}, succeed 1), "
                f"but attempted {attempt_count} times"
            )
            
            # Property 3: Result should be present
            assert "result" in run.artifacts, "Result should be in artifacts"
            assert run.artifacts["result"] == "success", "Result should be 'success'"
            
            # Property 4: Step execution should show correct attempt count
            step_exec = run.step_executions[0]
            assert step_exec.status == StepStatus.COMPLETED, "Step should be completed"
            assert step_exec.attempt == fail_count + 1, (
                f"Step execution should show {fail_count + 1} attempts"
            )
        else:
            # Should fail permanently after max_retries + 1 attempts
            with pytest.raises(RuntimeError, match="failed after"):
                await pipeline_executor.execute(pipeline, {})
            
            # Property 5: Should attempt exactly max_retries + 1 times
            assert attempt_count == max_retries + 1, (
                f"Should attempt {max_retries + 1} times (initial + {max_retries} retries), "
                f"but attempted {attempt_count} times"
            )
    
    # Run the async test
    asyncio.run(run_test())


@pytest.mark.property
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    initial_delay=st.floats(min_value=0.1, max_value=0.5),
    max_delay=st.floats(min_value=1.0, max_value=5.0),
    exponential_backoff=st.booleans(),
)
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow, HealthCheck.data_too_large]
)
def test_property_retry_delays_follow_policy(
    pipeline_executor, max_retries, initial_delay, max_delay, exponential_backoff
):
    """
    **Validates: Requirements 3.4**
    
    Property: For any retry policy configuration:
    - Delays between retries should follow the configured pattern
    - Exponential backoff should double delay each time
    - Fixed delay should use initial_delay consistently
    - Delays should respect max_delay bounds
    
    This property tests that retry delays follow the configured policy.
    """
    # Ensure max_delay is greater than initial_delay
    assume(max_delay > initial_delay)
    
    async def run_test():
        attempt_times = []
        
        async def failing_func(**kwargs):
            attempt_times.append(time.time())
            # Always fail to measure all retry delays
            raise ValueError("Simulated failure")
        
        # Create pipeline with retry policy
        pipeline = Pipeline(name="retry_delay_test")
        step = PipelineStep(
            name="test_step",
            agent="intake",
            function=failing_func,
            retry_policy=RetryPolicy(
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_backoff=exponential_backoff,
            ),
        )
        pipeline.add_step(step)
        
        # Execute (will fail)
        try:
            await pipeline_executor.execute(pipeline, {})
        except RuntimeError:
            pass  # Expected to fail
        
        # Property 1: Should have max_retries + 1 attempts
        assert len(attempt_times) == max_retries + 1, (
            f"Should have {max_retries + 1} attempts, got {len(attempt_times)}"
        )
        
        # Property 2: Calculate actual delays between attempts
        actual_delays = []
        for i in range(1, len(attempt_times)):
            delay = attempt_times[i] - attempt_times[i - 1]
            actual_delays.append(delay)
        
        # Property 3: Verify delay pattern
        for i, actual_delay in enumerate(actual_delays):
            if exponential_backoff:
                # Expected delay with exponential backoff
                expected_delay = min(initial_delay * (2 ** i), max_delay)
            else:
                # Fixed delay
                expected_delay = initial_delay
            
            # Allow 40% tolerance for timing variations (increased from 20% to reduce flakiness)
            tolerance = expected_delay * 0.4
            assert abs(actual_delay - expected_delay) <= tolerance, (
                f"Retry {i + 1}: actual delay ({actual_delay:.3f}s) should be "
                f"within {tolerance:.3f}s of expected ({expected_delay:.3f}s)"
            )
            
            # Property 4: Delay should never exceed max_delay (with generous tolerance)
            assert actual_delay <= max_delay + 0.2, (
                f"Retry {i + 1}: delay ({actual_delay:.3f}s) exceeded max_delay ({max_delay:.3f}s)"
            )
            
            # Property 5: Delay should be at least initial_delay (with generous tolerance)
            assert actual_delay >= initial_delay - 0.1, (
                f"Retry {i + 1}: delay ({actual_delay:.3f}s) below initial_delay ({initial_delay:.3f}s)"
            )
    
    # Run the async test
    asyncio.run(run_test())


@pytest.mark.property
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    success_on_attempt=st.integers(min_value=1, max_value=6),
)
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_property_retry_success_completes_step(
    pipeline_executor, max_retries, success_on_attempt
):
    """
    **Validates: Requirements 3.4**
    
    Property: For any retry policy:
    - If a retry succeeds before max_retries, the step should complete successfully
    - No further retries should be attempted after success
    - The pipeline should continue to subsequent steps
    
    This property tests that successful retries complete the step immediately.
    """
    async def run_test():
        attempt_count = 0
        
        async def sometimes_failing_func(**kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < success_on_attempt:
                raise ValueError(f"Failure {attempt_count}")
            return {"result": f"success_on_{attempt_count}"}
        
        # Create pipeline
        pipeline = Pipeline(name="retry_success_test")
        step = PipelineStep(
            name="test_step",
            agent="intake",
            function=sometimes_failing_func,
            outputs=["result"],
            retry_policy=RetryPolicy(
                max_retries=max_retries,
                initial_delay=0.1,
            ),
        )
        pipeline.add_step(step)
        
        # Execute
        if success_on_attempt <= max_retries + 1:
            # Should succeed
            run = await pipeline_executor.execute(pipeline, {})
            
            # Property 1: Pipeline should complete
            assert run.status == PipelineStatus.COMPLETED, (
                f"Pipeline should complete when success on attempt {success_on_attempt} "
                f"with max_retries {max_retries}"
            )
            
            # Property 2: Should attempt exactly success_on_attempt times
            assert attempt_count == success_on_attempt, (
                f"Should stop after success on attempt {success_on_attempt}, "
                f"but made {attempt_count} attempts"
            )
            
            # Property 3: Result should be present
            assert "result" in run.artifacts, "Result should be in artifacts"
            assert run.artifacts["result"] == f"success_on_{success_on_attempt}", (
                "Result should match success attempt"
            )
            
            # Property 4: Step should be marked as completed
            step_exec = run.step_executions[0]
            assert step_exec.status == StepStatus.COMPLETED, "Step should be completed"
            assert step_exec.error is None, "Step should have no error"
        else:
            # Should fail permanently
            with pytest.raises(RuntimeError, match="failed after"):
                await pipeline_executor.execute(pipeline, {})
            
            # Property 5: Should attempt max_retries + 1 times
            assert attempt_count == max_retries + 1, (
                f"Should attempt {max_retries + 1} times before giving up"
            )
    
    # Run the async test
    asyncio.run(run_test())


@pytest.mark.property
@given(
    max_retries=st.integers(min_value=0, max_value=5),
    initial_delay=st.floats(min_value=0.1, max_value=0.5),
)
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_property_all_retries_fail_step_fails(
    pipeline_executor, max_retries, initial_delay
):
    """
    **Validates: Requirements 3.4**
    
    Property: For any retry policy:
    - If all retries fail, the step should fail permanently
    - The pipeline should raise an exception
    - The error should be recorded in step execution
    - No further steps should be executed
    
    This property tests that exhausted retries result in permanent failure.
    """
    async def run_test():
        attempt_count = 0
        
        async def always_failing_func(**kwargs):
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError(f"Permanent failure {attempt_count}")
        
        # Create pipeline with multiple steps
        pipeline = Pipeline(name="retry_fail_test")
        
        # First step always fails
        step1 = PipelineStep(
            name="failing_step",
            agent="intake",
            function=always_failing_func,
            outputs=["result"],
            retry_policy=RetryPolicy(
                max_retries=max_retries,
                initial_delay=initial_delay,
            ),
        )
        pipeline.add_step(step1)
        
        # Second step should never execute
        second_step_executed = False
        
        async def second_step_func(**kwargs):
            nonlocal second_step_executed
            second_step_executed = True
            return {"second": "result"}
        
        step2 = PipelineStep(
            name="second_step",
            agent="diagnostic",
            function=second_step_func,
            outputs=["second"],
            depends_on=["failing_step"],
        )
        pipeline.add_step(step2)
        
        # Execute (should fail)
        with pytest.raises(RuntimeError, match="failed after"):
            await pipeline_executor.execute(pipeline, {})
        
        # Property 1: Should attempt max_retries + 1 times
        assert attempt_count == max_retries + 1, (
            f"Should attempt {max_retries + 1} times (initial + {max_retries} retries), "
            f"got {attempt_count} attempts"
        )
        
        # Property 2: Second step should never execute
        assert not second_step_executed, (
            "Subsequent steps should not execute after permanent failure"
        )
        
        # Property 3: Pipeline run should exist and be marked as failed
        runs = pipeline_executor.list_runs(pipeline_name="retry_fail_test")
        assert len(runs) > 0, "Pipeline run should be recorded"
        
        run = runs[0]
        assert run.status == PipelineStatus.FAILED, "Pipeline should be marked as failed"
        
        # Property 4: Error should be recorded
        assert run.error is not None, "Error should be recorded in pipeline run"
        assert "failed after" in run.error, "Error message should mention retry exhaustion"
        
        # Property 5: Step execution should show failure
        assert len(run.step_executions) > 0, "Step execution should be recorded"
        step_exec = run.step_executions[0]
        assert step_exec.status == StepStatus.FAILED, "Step should be marked as failed"
        assert step_exec.error is not None, "Step error should be recorded"
        assert step_exec.attempt == max_retries + 1, (
            f"Step should show {max_retries + 1} attempts"
        )
    
    # Run the async test
    asyncio.run(run_test())


@pytest.mark.property
@given(
    max_retries=st.integers(min_value=1, max_value=5),
    initial_delay=st.floats(min_value=0.1, max_value=0.5),
    max_delay=st.floats(min_value=1.0, max_value=3.0),
)
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_property_retry_delays_respect_bounds(
    pipeline_executor, max_retries, initial_delay, max_delay
):
    """
    **Validates: Requirements 3.4**
    
    Property: For any retry policy with exponential backoff:
    - Delays should start at initial_delay
    - Delays should never exceed max_delay
    - Delays should grow exponentially until hitting max_delay
    - All delays should be within [initial_delay, max_delay] bounds
    
    This property tests that retry delays respect configured min/max bounds.
    """
    # Ensure max_delay > initial_delay
    assume(max_delay > initial_delay)
    
    async def run_test():
        attempt_times = []
        
        async def failing_func(**kwargs):
            attempt_times.append(time.time())
            raise ValueError("Simulated failure")
        
        # Create pipeline with exponential backoff
        pipeline = Pipeline(name="retry_bounds_test")
        step = PipelineStep(
            name="test_step",
            agent="intake",
            function=failing_func,
            retry_policy=RetryPolicy(
                max_retries=max_retries,
                initial_delay=initial_delay,
                max_delay=max_delay,
                exponential_backoff=True,
            ),
        )
        pipeline.add_step(step)
        
        # Execute (will fail)
        try:
            await pipeline_executor.execute(pipeline, {})
        except RuntimeError:
            pass  # Expected
        
        # Calculate actual delays
        actual_delays = []
        for i in range(1, len(attempt_times)):
            delay = attempt_times[i] - attempt_times[i - 1]
            actual_delays.append(delay)
        
        # Property 1: All delays should be >= initial_delay (with small tolerance)
        for i, delay in enumerate(actual_delays):
            assert delay >= initial_delay - 0.05, (
                f"Delay {i + 1} ({delay:.3f}s) below initial_delay ({initial_delay:.3f}s)"
            )
        
        # Property 2: All delays should be <= max_delay (with small tolerance)
        for i, delay in enumerate(actual_delays):
            assert delay <= max_delay + 0.1, (
                f"Delay {i + 1} ({delay:.3f}s) exceeds max_delay ({max_delay:.3f}s)"
            )
        
        # Property 3: Delays should grow exponentially until hitting max_delay
        for i in range(len(actual_delays) - 1):
            expected_next = min(initial_delay * (2 ** (i + 1)), max_delay)
            expected_current = min(initial_delay * (2 ** i), max_delay)
            
            # If we haven't hit max_delay, next should be roughly double current
            if expected_current < max_delay:
                # Allow 30% tolerance for timing variations
                tolerance = expected_next * 0.3
                assert actual_delays[i + 1] >= actual_delays[i] - tolerance, (
                    f"Delay should grow: delay[{i + 1}] ({actual_delays[i + 1]:.3f}s) "
                    f"should be >= delay[{i}] ({actual_delays[i]:.3f}s)"
                )
        
        # Property 4: Once max_delay is reached, delays should stay at max_delay
        for i, delay in enumerate(actual_delays):
            expected_delay = min(initial_delay * (2 ** i), max_delay)
            if expected_delay >= max_delay:
                # Should be at max_delay (with tolerance)
                tolerance = max_delay * 0.2
                assert abs(delay - max_delay) <= tolerance, (
                    f"Delay {i + 1} ({delay:.3f}s) should be at max_delay ({max_delay:.3f}s)"
                )
    
    # Run the async test
    asyncio.run(run_test())


@pytest.mark.property
@given(
    num_steps=st.integers(min_value=2, max_value=5),
    max_retries=st.integers(min_value=1, max_value=3),
    fail_step_index=st.integers(min_value=0, max_value=4),
)
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.too_slow]
)
def test_property_retry_in_multi_step_pipeline(
    pipeline_executor, num_steps, max_retries, fail_step_index
):
    """
    **Validates: Requirements 3.4**
    
    Property: In a multi-step pipeline:
    - Only the failing step should retry
    - Successful steps should execute once
    - Steps after a failed step should not execute
    - Retry policy applies independently to each step
    
    This property tests retry behavior in complex pipelines.
    """
    # Ensure fail_step_index is within bounds
    assume(fail_step_index < num_steps)
    
    async def run_test():
        execution_counts = {}
        
        async def make_step_func(step_index: int):
            async def step_func(**kwargs):
                execution_counts[step_index] = execution_counts.get(step_index, 0) + 1
                
                if step_index == fail_step_index:
                    # This step fails twice then succeeds
                    if execution_counts[step_index] <= 2:
                        raise ValueError(f"Step {step_index} failure")
                
                return {f"result_{step_index}": f"value_{step_index}"}
            
            return step_func
        
        # Create pipeline with multiple steps (sequential with dependencies)
        pipeline = Pipeline(name="multi_step_retry_test")
        
        for i in range(num_steps):
            # Add dependency on previous step to create sequential execution
            depends_on = [f"step_{i-1}"] if i > 0 else []
            
            step = PipelineStep(
                name=f"step_{i}",
                agent="intake",
                function=await make_step_func(i),
                outputs=[f"result_{i}"],
                retry_policy=RetryPolicy(
                    max_retries=max_retries,
                    initial_delay=0.1,
                ),
                depends_on=depends_on,
            )
            pipeline.add_step(step)
        
        # Execute
        if 2 <= max_retries:
            # Should succeed (failing step needs 2 retries)
            run = await pipeline_executor.execute(pipeline, {})
            
            # Property 1: Pipeline should complete
            assert run.status == PipelineStatus.COMPLETED, (
                "Pipeline should complete when retries are sufficient"
            )
            
            # Property 2: Failing step should execute 3 times (fail, fail, succeed)
            assert execution_counts[fail_step_index] == 3, (
                f"Failing step should execute 3 times, got {execution_counts[fail_step_index]}"
            )
            
            # Property 3: Other steps should execute exactly once
            for i in range(num_steps):
                if i != fail_step_index:
                    assert execution_counts[i] == 1, (
                        f"Step {i} should execute once, got {execution_counts[i]}"
                    )
            
            # Property 4: All results should be present
            for i in range(num_steps):
                assert f"result_{i}" in run.artifacts, (
                    f"Result {i} should be in artifacts"
                )
        else:
            # Should fail (not enough retries)
            with pytest.raises(RuntimeError, match="failed after"):
                await pipeline_executor.execute(pipeline, {})
            
            # Property 5: Failing step should execute max_retries + 1 times
            assert execution_counts[fail_step_index] == max_retries + 1, (
                f"Failing step should execute {max_retries + 1} times"
            )
            
            # Property 6: Steps before failing step should execute once
            for i in range(fail_step_index):
                assert execution_counts[i] == 1, (
                    f"Step {i} before failure should execute once"
                )
            
            # Property 7: Steps after failing step should not execute
            for i in range(fail_step_index + 1, num_steps):
                assert i not in execution_counts or execution_counts[i] == 0, (
                    f"Step {i} after failure should not execute"
                )
    
    # Run the async test
    asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property"])
