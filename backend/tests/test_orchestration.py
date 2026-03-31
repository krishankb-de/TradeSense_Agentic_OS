"""
Unit tests for orchestration module.

Tests pipeline execution, artifact tracking, secrets management, and retry policies.
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import datetime
from typing import Dict, Any

from orchestration.pipeline import (
    Pipeline,
    PipelineExecutor,
    PipelineStep,
    PipelineStatus,
    RetryPolicy,
    SecretsManager,
    StepStatus,
)
from orchestration.workflow import (
    IntakeWorkflow,
    DiagnosticWorkflow,
    FulfillmentWorkflow,
    get_workflow,
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
# Secrets Manager Tests
# ============================================================================


@pytest.mark.asyncio
async def test_secrets_manager_set_get(secrets_manager):
    """Test setting and getting secrets."""
    await secrets_manager.set_secret("test_key", "test_value")
    value = await secrets_manager.get_secret("test_key")
    assert value == "test_value"


@pytest.mark.asyncio
async def test_secrets_manager_get_nonexistent(secrets_manager):
    """Test getting a non-existent secret returns None."""
    value = await secrets_manager.get_secret("nonexistent")
    assert value is None


@pytest.mark.asyncio
async def test_secrets_manager_delete(secrets_manager):
    """Test deleting a secret."""
    await secrets_manager.set_secret("test_key", "test_value")
    deleted = await secrets_manager.delete_secret("test_key")
    assert deleted is True
    value = await secrets_manager.get_secret("test_key")
    assert value is None


@pytest.mark.asyncio
async def test_secrets_manager_list(secrets_manager):
    """Test listing secret keys."""
    await secrets_manager.set_secret("key1", "value1")
    await secrets_manager.set_secret("key2", "value2")
    keys = await secrets_manager.list_secrets()
    assert "key1" in keys
    assert "key2" in keys
    assert len(keys) == 2


@pytest.mark.asyncio
async def test_secrets_manager_webrtc_credentials(secrets_manager):
    """Test storing WebRTC credentials (Requirement 3.3)."""
    await secrets_manager.set_secret("webrtc_turn_username", "user123")
    await secrets_manager.set_secret("webrtc_turn_password", "pass456")
    
    username = await secrets_manager.get_secret("webrtc_turn_username")
    password = await secrets_manager.get_secret("webrtc_turn_password")
    
    assert username == "user123"
    assert password == "pass456"


@pytest.mark.asyncio
async def test_secrets_manager_jitsi_credentials(secrets_manager):
    """Test storing Jitsi credentials (Requirement 3.3)."""
    await secrets_manager.set_secret("jitsi_jwt_app_id", "app123")
    await secrets_manager.set_secret("jitsi_jwt_secret", "secret456")
    
    app_id = await secrets_manager.get_secret("jitsi_jwt_app_id")
    secret = await secrets_manager.get_secret("jitsi_jwt_secret")
    
    assert app_id == "app123"
    assert secret == "secret456"


# ============================================================================
# Pipeline Tests
# ============================================================================


def test_pipeline_creation():
    """Test creating a pipeline."""
    pipeline = Pipeline(name="test_pipeline", description="Test pipeline")
    assert pipeline.name == "test_pipeline"
    assert pipeline.description == "Test pipeline"
    assert len(pipeline.steps) == 0


def test_pipeline_add_step():
    """Test adding steps to a pipeline."""
    pipeline = Pipeline(name="test_pipeline")
    step = PipelineStep(name="step1", agent="intake", inputs=[], outputs=[])
    pipeline.add_step(step)
    assert len(pipeline.steps) == 1
    assert pipeline.steps[0].name == "step1"


def test_pipeline_validate_dependencies_success():
    """Test validating pipeline dependencies."""
    pipeline = Pipeline(name="test_pipeline")
    pipeline.add_step(PipelineStep(name="step1", agent="intake"))
    pipeline.add_step(
        PipelineStep(name="step2", agent="diagnostic", depends_on=["step1"])
    )
    assert pipeline.validate_dependencies() is True


def test_pipeline_validate_dependencies_failure():
    """Test validating pipeline with invalid dependencies."""
    pipeline = Pipeline(name="test_pipeline")
    pipeline.add_step(
        PipelineStep(name="step1", agent="intake", depends_on=["nonexistent"])
    )
    with pytest.raises(ValueError, match="depends on non-existent step"):
        pipeline.validate_dependencies()


# ============================================================================
# Pipeline Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_pipeline_execution_simple(pipeline_executor):
    """Test executing a simple pipeline (Requirement 3.1)."""
    
    async def step_func(**kwargs):
        return {"result": "success"}
    
    pipeline = Pipeline(name="simple_pipeline")
    step = PipelineStep(
        name="step1",
        agent="intake",
        function=step_func,
        inputs=[],
        outputs=["result"],
    )
    pipeline.add_step(step)
    
    run = await pipeline_executor.execute(pipeline, {})
    
    assert run.status == PipelineStatus.COMPLETED
    assert run.artifacts["result"] == "success"
    assert run.duration is not None
    assert run.duration > 0


@pytest.mark.asyncio
async def test_pipeline_execution_with_dependencies(pipeline_executor):
    """Test executing a pipeline with dependencies (Requirement 3.1)."""
    
    async def step1_func(**kwargs):
        return {"value": 10}
    
    async def step2_func(value, **kwargs):
        return {"doubled": value * 2}
    
    pipeline = Pipeline(name="dependency_pipeline")
    pipeline.add_step(
        PipelineStep(
            name="step1",
            agent="intake",
            function=step1_func,
            outputs=["value"],
        )
    )
    pipeline.add_step(
        PipelineStep(
            name="step2",
            agent="diagnostic",
            function=step2_func,
            inputs=["value"],
            outputs=["doubled"],
            depends_on=["step1"],
        )
    )
    
    run = await pipeline_executor.execute(pipeline, {})
    
    assert run.status == PipelineStatus.COMPLETED
    assert run.artifacts["value"] == 10
    assert run.artifacts["doubled"] == 20


@pytest.mark.asyncio
async def test_pipeline_execution_with_retry(pipeline_executor):
    """Test pipeline retry policy (Requirement 3.1)."""
    
    attempt_count = 0
    
    async def failing_func(**kwargs):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ValueError("Simulated failure")
        return {"result": "success"}
    
    pipeline = Pipeline(name="retry_pipeline")
    step = PipelineStep(
        name="step1",
        agent="intake",
        function=failing_func,
        outputs=["result"],
        retry_policy=RetryPolicy(max_retries=3, initial_delay=0.1),
    )
    pipeline.add_step(step)
    
    run = await pipeline_executor.execute(pipeline, {})
    
    assert run.status == PipelineStatus.COMPLETED
    assert attempt_count == 3
    assert run.artifacts["result"] == "success"


@pytest.mark.asyncio
async def test_pipeline_execution_failure(pipeline_executor):
    """Test pipeline execution failure."""
    
    async def failing_func(**kwargs):
        raise ValueError("Permanent failure")
    
    pipeline = Pipeline(name="failing_pipeline")
    step = PipelineStep(
        name="step1",
        agent="intake",
        function=failing_func,
        retry_policy=RetryPolicy(max_retries=1, initial_delay=0.1),
    )
    pipeline.add_step(step)
    
    with pytest.raises(RuntimeError, match="failed after"):
        await pipeline_executor.execute(pipeline, {})


@pytest.mark.asyncio
async def test_pipeline_execution_timeout(pipeline_executor):
    """Test pipeline step timeout."""
    
    async def slow_func(**kwargs):
        await asyncio.sleep(2.0)
        return {"result": "success"}
    
    pipeline = Pipeline(name="timeout_pipeline")
    step = PipelineStep(
        name="step1",
        agent="intake",
        function=slow_func,
        timeout=0.5,
        retry_policy=RetryPolicy(max_retries=0),
    )
    pipeline.add_step(step)
    
    with pytest.raises(RuntimeError):
        await pipeline_executor.execute(pipeline, {})


@pytest.mark.asyncio
async def test_pipeline_artifact_tracking(pipeline_executor):
    """Test artifact tracking (Requirement 3.1)."""
    
    async def step1_func(**kwargs):
        return {"artifact1": "value1"}
    
    async def step2_func(**kwargs):
        return {"artifact2": "value2"}
    
    pipeline = Pipeline(name="artifact_pipeline")
    pipeline.add_step(
        PipelineStep(
            name="step1",
            agent="intake",
            function=step1_func,
            outputs=["artifact1"],
        )
    )
    pipeline.add_step(
        PipelineStep(
            name="step2",
            agent="diagnostic",
            function=step2_func,
            outputs=["artifact2"],
        )
    )
    
    run = await pipeline_executor.execute(pipeline, {"input": "test"})
    
    assert run.status == PipelineStatus.COMPLETED
    assert "input" in run.artifacts
    assert "artifact1" in run.artifacts
    assert "artifact2" in run.artifacts


# ============================================================================
# Pipeline Monitoring Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_pipeline_run(pipeline_executor):
    """Test retrieving pipeline run (Requirement 3.6)."""
    
    async def step_func(**kwargs):
        return {"result": "success"}
    
    pipeline = Pipeline(name="test_pipeline")
    pipeline.add_step(
        PipelineStep(name="step1", agent="intake", function=step_func)
    )
    
    run = await pipeline_executor.execute(pipeline, {})
    retrieved_run = pipeline_executor.get_run(run.id)
    
    assert retrieved_run is not None
    assert retrieved_run.id == run.id
    assert retrieved_run.status == PipelineStatus.COMPLETED


@pytest.mark.asyncio
async def test_list_pipeline_runs(pipeline_executor):
    """Test listing pipeline runs (Requirement 3.6)."""
    
    async def step_func(**kwargs):
        return {"result": "success"}
    
    pipeline = Pipeline(name="test_pipeline")
    pipeline.add_step(
        PipelineStep(name="step1", agent="intake", function=step_func)
    )
    
    # Execute multiple runs
    run1 = await pipeline_executor.execute(pipeline, {})
    run2 = await pipeline_executor.execute(pipeline, {})
    
    runs = pipeline_executor.list_runs()
    
    assert len(runs) >= 2
    assert any(r.id == run1.id for r in runs)
    assert any(r.id == run2.id for r in runs)


@pytest.mark.asyncio
async def test_list_pipeline_runs_filtered(pipeline_executor):
    """Test listing pipeline runs filtered by name (Requirement 3.6)."""
    
    async def step_func(**kwargs):
        return {"result": "success"}
    
    pipeline1 = Pipeline(name="pipeline1")
    pipeline1.add_step(
        PipelineStep(name="step1", agent="intake", function=step_func)
    )
    
    pipeline2 = Pipeline(name="pipeline2")
    pipeline2.add_step(
        PipelineStep(name="step1", agent="intake", function=step_func)
    )
    
    await pipeline_executor.execute(pipeline1, {})
    await pipeline_executor.execute(pipeline2, {})
    
    runs = pipeline_executor.list_runs(pipeline_name="pipeline1")
    
    assert all(r.pipeline_name == "pipeline1" for r in runs)


# ============================================================================
# Workflow Template Tests
# ============================================================================


def test_intake_workflow_creation():
    """Test creating intake workflow."""
    pipeline = IntakeWorkflow.create()
    assert pipeline.name == "intake_workflow"
    assert len(pipeline.steps) == 5
    assert pipeline.steps[0].name == "extract_lead_info"
    assert pipeline.steps[0].agent == "intake"


def test_diagnostic_workflow_creation():
    """Test creating diagnostic workflow."""
    pipeline = DiagnosticWorkflow.create()
    assert pipeline.name == "diagnostic_workflow"
    assert len(pipeline.steps) == 5
    assert pipeline.steps[0].name == "analyze_issue"
    assert pipeline.steps[0].agent == "diagnostic"


def test_fulfillment_workflow_creation():
    """Test creating fulfillment workflow."""
    pipeline = FulfillmentWorkflow.create()
    assert pipeline.name == "fulfillment_workflow"
    assert len(pipeline.steps) == 5
    assert pipeline.steps[0].name == "optimize_schedule"
    assert pipeline.steps[0].agent == "fulfillment"


def test_get_workflow():
    """Test getting workflow by type."""
    intake = get_workflow("intake")
    assert intake is not None
    assert intake.name == "intake_workflow"
    
    diagnostic = get_workflow("diagnostic")
    assert diagnostic is not None
    assert diagnostic.name == "diagnostic_workflow"
    
    fulfillment = get_workflow("fulfillment")
    assert fulfillment is not None
    assert fulfillment.name == "fulfillment_workflow"
    
    invalid = get_workflow("invalid")
    assert invalid is None


def test_workflow_dependencies():
    """Test workflow step dependencies are valid."""
    workflows = [
        IntakeWorkflow.create(),
        DiagnosticWorkflow.create(),
        FulfillmentWorkflow.create(),
    ]
    
    for workflow in workflows:
        assert workflow.validate_dependencies() is True


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_intake_workflow_execution(pipeline_executor):
    """Test executing intake workflow end-to-end."""
    
    # Mock step functions
    async def extract_lead_info(raw_input, source, **kwargs):
        return {"lead_data": {"customer": "John Doe", "issue": "AC broken"}}
    
    async def classify_urgency(lead_data, **kwargs):
        return {"triage_result": {"urgency": "urgent", "service_type": "HVAC"}}
    
    async def check_parts(triage_result, **kwargs):
        return {"parts_availability": {"capacitor": "in-stock"}}
    
    async def assign_technician(triage_result, parts_availability, **kwargs):
        return {"assignment": {"technician_id": "tech123"}}
    
    async def create_lead(lead_data, triage_result, assignment, **kwargs):
        return {"lead_id": "lead123"}
    
    # Create workflow and assign functions
    pipeline = IntakeWorkflow.create()
    pipeline.steps[0].function = extract_lead_info
    pipeline.steps[1].function = classify_urgency
    pipeline.steps[2].function = check_parts
    pipeline.steps[3].function = assign_technician
    pipeline.steps[4].function = create_lead
    
    # Execute
    run = await pipeline_executor.execute(
        pipeline, {"raw_input": "My AC is broken", "source": "voice"}
    )
    
    assert run.status == PipelineStatus.COMPLETED
    assert "lead_id" in run.artifacts
    assert run.artifacts["lead_id"] == "lead123"


@pytest.mark.asyncio
async def test_parallel_step_execution(pipeline_executor):
    """Test that independent steps execute in parallel."""
    
    execution_order = []
    
    async def step1(**kwargs):
        execution_order.append("step1_start")
        await asyncio.sleep(0.1)
        execution_order.append("step1_end")
        return {"result1": "value1"}
    
    async def step2(**kwargs):
        execution_order.append("step2_start")
        await asyncio.sleep(0.1)
        execution_order.append("step2_end")
        return {"result2": "value2"}
    
    pipeline = Pipeline(name="parallel_pipeline")
    pipeline.add_step(
        PipelineStep(name="step1", agent="intake", function=step1)
    )
    pipeline.add_step(
        PipelineStep(name="step2", agent="diagnostic", function=step2)
    )
    
    run = await pipeline_executor.execute(pipeline, {})
    
    assert run.status == PipelineStatus.COMPLETED
    # Both steps should start before either ends (parallel execution)
    assert execution_order.index("step1_start") < execution_order.index("step1_end")
    assert execution_order.index("step2_start") < execution_order.index("step2_end")


