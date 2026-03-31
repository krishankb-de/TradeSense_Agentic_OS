"""
Manual test script for orchestration module.

This script demonstrates the orchestration functionality without pytest-asyncio.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from orchestration.pipeline import (
    Pipeline,
    PipelineExecutor,
    PipelineStep,
    PipelineStatus,
    RetryPolicy,
    SecretsManager,
)
from orchestration.workflow import (
    IntakeWorkflow,
    DiagnosticWorkflow,
    FulfillmentWorkflow,
)


async def test_secrets_manager():
    """Test secrets manager functionality."""
    print("\n=== Testing Secrets Manager ===")
    
    sm = SecretsManager()
    
    # Test WebRTC credentials (Requirement 3.3)
    await sm.set_secret("webrtc_turn_username", "user123")
    await sm.set_secret("webrtc_turn_password", "pass456")
    
    username = await sm.get_secret("webrtc_turn_username")
    password = await sm.get_secret("webrtc_turn_password")
    
    print(f"✓ WebRTC username: {username}")
    print(f"✓ WebRTC password: {password}")
    
    # Test Jitsi credentials (Requirement 3.3)
    await sm.set_secret("jitsi_jwt_app_id", "app123")
    await sm.set_secret("jitsi_jwt_secret", "secret456")
    
    app_id = await sm.get_secret("jitsi_jwt_app_id")
    secret = await sm.get_secret("jitsi_jwt_secret")
    
    print(f"✓ Jitsi app_id: {app_id}")
    print(f"✓ Jitsi secret: {secret}")
    
    # List all secrets
    keys = await sm.list_secrets()
    print(f"✓ Total secrets stored: {len(keys)}")
    
    print("✅ Secrets Manager tests passed!")


async def test_simple_pipeline():
    """Test simple pipeline execution (Requirement 3.1)."""
    print("\n=== Testing Simple Pipeline Execution ===")
    
    async def step_func(**kwargs):
        print("  → Executing step function...")
        await asyncio.sleep(0.1)
        return {"result": "success", "value": 42}
    
    executor = PipelineExecutor()
    
    pipeline = Pipeline(name="simple_pipeline", description="Test pipeline")
    step = PipelineStep(
        name="step1",
        agent="intake",
        function=step_func,
        outputs=["result", "value"],
    )
    pipeline.add_step(step)
    
    print(f"Pipeline: {pipeline.name}")
    print(f"Steps: {len(pipeline.steps)}")
    
    run = await executor.execute(pipeline, {"input": "test"})
    
    print(f"✓ Status: {run.status}")
    print(f"✓ Duration: {run.duration:.3f}s")
    print(f"✓ Artifacts: {run.artifacts}")
    
    assert run.status == PipelineStatus.COMPLETED
    assert run.artifacts["result"] == "success"
    assert run.artifacts["value"] == 42
    
    print("✅ Simple pipeline tests passed!")


async def test_pipeline_with_dependencies():
    """Test pipeline with dependencies (Requirement 3.1)."""
    print("\n=== Testing Pipeline with Dependencies ===")
    
    async def step1_func(**kwargs):
        print("  → Step 1: Generating value...")
        await asyncio.sleep(0.1)
        return {"value": 10}
    
    async def step2_func(value, **kwargs):
        print(f"  → Step 2: Doubling value {value}...")
        await asyncio.sleep(0.1)
        return {"doubled": value * 2}
    
    async def step3_func(doubled, **kwargs):
        print(f"  → Step 3: Adding 5 to {doubled}...")
        await asyncio.sleep(0.1)
        return {"final": doubled + 5}
    
    executor = PipelineExecutor()
    
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
    pipeline.add_step(
        PipelineStep(
            name="step3",
            agent="fulfillment",
            function=step3_func,
            inputs=["doubled"],
            outputs=["final"],
            depends_on=["step2"],
        )
    )
    
    run = await executor.execute(pipeline, {})
    
    print(f"✓ Status: {run.status}")
    print(f"✓ Duration: {run.duration:.3f}s")
    print(f"✓ Value: {run.artifacts['value']}")
    print(f"✓ Doubled: {run.artifacts['doubled']}")
    print(f"✓ Final: {run.artifacts['final']}")
    
    assert run.status == PipelineStatus.COMPLETED
    assert run.artifacts["value"] == 10
    assert run.artifacts["doubled"] == 20
    assert run.artifacts["final"] == 25
    
    print("✅ Dependency pipeline tests passed!")


async def test_retry_policy():
    """Test retry policy (Requirement 3.1)."""
    print("\n=== Testing Retry Policy ===")
    
    attempt_count = 0
    
    async def failing_func(**kwargs):
        nonlocal attempt_count
        attempt_count += 1
        print(f"  → Attempt {attempt_count}...")
        if attempt_count < 3:
            raise ValueError("Simulated failure")
        return {"result": "success"}
    
    executor = PipelineExecutor()
    
    pipeline = Pipeline(name="retry_pipeline")
    step = PipelineStep(
        name="step1",
        agent="intake",
        function=failing_func,
        outputs=["result"],
        retry_policy=RetryPolicy(max_retries=3, initial_delay=0.1),
    )
    pipeline.add_step(step)
    
    run = await executor.execute(pipeline, {})
    
    print(f"✓ Status: {run.status}")
    print(f"✓ Total attempts: {attempt_count}")
    print(f"✓ Result: {run.artifacts['result']}")
    
    assert run.status == PipelineStatus.COMPLETED
    assert attempt_count == 3
    
    print("✅ Retry policy tests passed!")


async def test_workflow_templates():
    """Test workflow templates."""
    print("\n=== Testing Workflow Templates ===")
    
    intake = IntakeWorkflow.create()
    print(f"✓ Intake workflow: {intake.name} ({len(intake.steps)} steps)")
    assert intake.validate_dependencies()
    
    diagnostic = DiagnosticWorkflow.create()
    print(f"✓ Diagnostic workflow: {diagnostic.name} ({len(diagnostic.steps)} steps)")
    assert diagnostic.validate_dependencies()
    
    fulfillment = FulfillmentWorkflow.create()
    print(f"✓ Fulfillment workflow: {fulfillment.name} ({len(fulfillment.steps)} steps)")
    assert fulfillment.validate_dependencies()
    
    print("✅ Workflow template tests passed!")


async def test_pipeline_monitoring():
    """Test pipeline monitoring (Requirement 3.6)."""
    print("\n=== Testing Pipeline Monitoring ===")
    
    async def step_func(**kwargs):
        await asyncio.sleep(0.1)
        return {"result": "success"}
    
    executor = PipelineExecutor()
    
    pipeline = Pipeline(name="test_pipeline")
    pipeline.add_step(
        PipelineStep(name="step1", agent="intake", function=step_func)
    )
    
    # Execute multiple runs
    run1 = await executor.execute(pipeline, {"input": "test1"})
    run2 = await executor.execute(pipeline, {"input": "test2"})
    
    # Get specific run
    retrieved = executor.get_run(run1.id)
    print(f"✓ Retrieved run: {retrieved.id}")
    assert retrieved.id == run1.id
    
    # List all runs
    runs = executor.list_runs()
    print(f"✓ Total runs: {len(runs)}")
    assert len(runs) >= 2
    
    # List filtered runs
    filtered = executor.list_runs(pipeline_name="test_pipeline")
    print(f"✓ Filtered runs: {len(filtered)}")
    assert all(r.pipeline_name == "test_pipeline" for r in filtered)
    
    print("✅ Pipeline monitoring tests passed!")


async def main():
    """Run all tests."""
    print("=" * 70)
    print("TradeSense Orchestration Module Tests")
    print("=" * 70)
    
    try:
        await test_secrets_manager()
        await test_simple_pipeline()
        await test_pipeline_with_dependencies()
        await test_retry_policy()
        await test_workflow_templates()
        await test_pipeline_monitoring()
        
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
