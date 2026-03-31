"""
Core pipeline orchestration for TradeSense.

Provides lightweight pipeline execution with async/await, artifact tracking,
secrets management, and retry policies. This is a simplified alternative to
ZenML for cloud-based deployments.

**Validates: Requirements 3.1, 3.3, 3.6, 3.8**
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, Field

from orchestration.telemetry import get_telemetry_manager

logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    """Pipeline execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Pipeline step execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RetryPolicy(BaseModel):
    """Retry policy configuration for pipeline steps."""

    max_retries: int = Field(default=3, ge=0, le=10)
    initial_delay: float = Field(default=1.0, ge=0.1)
    max_delay: float = Field(default=60.0, ge=1.0)
    exponential_backoff: bool = Field(default=True)
    retry_on_exceptions: List[str] = Field(
        default_factory=lambda: ["Exception"]
    )  # Exception class names


class PipelineStep(BaseModel):
    """Definition of a single pipeline step."""

    model_config = {"arbitrary_types_allowed": True}

    name: str = Field(..., min_length=1)
    agent: str = Field(..., description="Agent type: intake, diagnostic, fulfillment")
    function: Optional[Callable] = Field(
        None, exclude=True, description="Async function to execute"
    )
    inputs: List[str] = Field(default_factory=list)
    outputs: List[str] = Field(default_factory=list)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    timeout: Optional[float] = Field(None, ge=1.0, description="Timeout in seconds")
    depends_on: List[str] = Field(
        default_factory=list, description="Names of steps this depends on"
    )


class StepExecution(BaseModel):
    """Record of a step execution."""

    step_name: str
    status: StepStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    attempt: int = 0
    error: Optional[str] = None
    outputs: Dict[str, Any] = Field(default_factory=dict)


class PipelineRun(BaseModel):
    """Record of a pipeline execution."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_name: str
    status: PipelineStatus = PipelineStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    step_executions: List[StepExecution] = Field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Pipeline(BaseModel):
    """Pipeline definition with steps and configuration."""

    name: str = Field(..., min_length=1)
    description: str = ""
    steps: List[PipelineStep] = Field(default_factory=list)
    enable_cache: bool = Field(default=False)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_step(self, step: PipelineStep) -> "Pipeline":
        """Add a step to the pipeline."""
        self.steps.append(step)
        return self

    def validate_dependencies(self) -> bool:
        """Validate that all step dependencies exist."""
        step_names = {step.name for step in self.steps}
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_names:
                    raise ValueError(
                        f"Step '{step.name}' depends on non-existent step '{dep}'"
                    )
        return True


class SecretsManager:
    """
    Simple secrets manager for storing sensitive configuration.
    
    **Validates: Requirement 3.3** - Manage secrets for WebRTC, Jitsi, email,
    and database credentials.
    
    In production, this should be replaced with a proper secrets backend
    like HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault.
    """

    def __init__(self):
        self._secrets: Dict[str, str] = {}
        logger.info("Initialized SecretsManager (in-memory)")

    async def set_secret(self, key: str, value: str) -> None:
        """Store a secret."""
        self._secrets[key] = value
        logger.debug(f"Secret '{key}' stored")

    async def get_secret(self, key: str) -> Optional[str]:
        """Retrieve a secret."""
        value = self._secrets.get(key)
        if value is None:
            logger.warning(f"Secret '{key}' not found")
        return value

    async def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        if key in self._secrets:
            del self._secrets[key]
            logger.debug(f"Secret '{key}' deleted")
            return True
        return False

    async def list_secrets(self) -> List[str]:
        """List all secret keys (not values)."""
        return list(self._secrets.keys())


class PipelineExecutor:
    """
    Executes pipelines with async/await, retry policies, and artifact tracking.
    
    **Validates: Requirement 3.1** - Coordinate all agent execution through
    declarative pipelines.
    **Validates: Requirement 3.8** - Emit telemetry to Langfuse and Arize Phoenix
    """

    def __init__(self, secrets_manager: Optional[SecretsManager] = None):
        self.secrets_manager = secrets_manager or SecretsManager()
        self._runs: Dict[str, PipelineRun] = {}
        self._artifact_cache: Dict[str, Any] = {}
        self._telemetry = get_telemetry_manager()
        logger.info("Initialized PipelineExecutor with telemetry")

    async def execute(
        self, pipeline: Pipeline, inputs: Dict[str, Any]
    ) -> PipelineRun:
        """
        Execute a pipeline with the given inputs.
        
        **Validates: Requirement 3.1** - Execute declarative pipelines with
        dependency management and artifact tracking.
        **Validates: Requirement 3.8** - Emit telemetry to Langfuse
        """
        # Validate pipeline
        pipeline.validate_dependencies()

        # Create run record
        run = PipelineRun(
            pipeline_name=pipeline.name,
            status=PipelineStatus.RUNNING,
            start_time=datetime.utcnow(),
            inputs=inputs,
        )
        self._runs[run.id] = run

        logger.info(
            f"Starting pipeline '{pipeline.name}' (run_id={run.id}) with inputs: {list(inputs.keys())}"
        )

        # Start telemetry trace
        trace = self._telemetry.trace_pipeline_start(
            pipeline_name=pipeline.name,
            run_id=run.id,
            inputs=inputs,
            metadata=pipeline.metadata,
        )

        try:
            # Execute steps in dependency order
            executed_steps = set()
            artifacts = dict(inputs)  # Start with input artifacts

            while len(executed_steps) < len(pipeline.steps):
                # Find steps ready to execute
                ready_steps = [
                    step
                    for step in pipeline.steps
                    if step.name not in executed_steps
                    and all(dep in executed_steps for dep in step.depends_on)
                ]

                if not ready_steps:
                    raise RuntimeError(
                        "Pipeline has circular dependencies or unreachable steps"
                    )

                # Execute ready steps in parallel
                tasks = [
                    self._execute_step(step, artifacts, run) for step in ready_steps
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Process results - stop immediately on first failure
                for step, result in zip(ready_steps, results):
                    if isinstance(result, Exception):
                        # Mark pipeline as failed and stop execution
                        run.status = PipelineStatus.FAILED
                        raise result
                    executed_steps.add(step.name)
                    # Merge step outputs into artifacts
                    artifacts.update(result)

            # Pipeline completed successfully
            run.status = PipelineStatus.COMPLETED
            run.artifacts = artifacts
            run.end_time = datetime.utcnow()
            run.duration = (run.end_time - run.start_time).total_seconds()

            # End telemetry trace
            self._telemetry.trace_pipeline_end(
                run_id=run.id,
                status="completed",
                outputs=artifacts,
            )

            # Record success metric
            self._telemetry.record_metric(
                "pipeline.execution.duration",
                run.duration,
                tags={
                    "pipeline": pipeline.name,
                    "status": "completed",
                },
            )

            logger.info(
                f"Pipeline '{pipeline.name}' completed successfully in {run.duration:.2f}s"
            )

        except Exception as e:
            run.status = PipelineStatus.FAILED
            run.error = str(e)
            run.end_time = datetime.utcnow()
            if run.start_time:
                run.duration = (run.end_time - run.start_time).total_seconds()

            # End telemetry trace with error
            self._telemetry.trace_pipeline_end(
                run_id=run.id,
                status="failed",
                error=str(e),
            )

            # Capture error in Sentry
            self._telemetry.capture_error(
                e,
                context={
                    "pipeline": pipeline.name,
                    "run_id": run.id,
                    "inputs": inputs,
                },
            )

            # Record failure metric
            self._telemetry.record_metric(
                "pipeline.execution.duration",
                run.duration or 0,
                tags={
                    "pipeline": pipeline.name,
                    "status": "failed",
                },
            )

            logger.error(
                f"Pipeline '{pipeline.name}' failed: {e}", exc_info=True
            )
            raise

        return run

    async def _execute_step(
        self, step: PipelineStep, artifacts: Dict[str, Any], run: PipelineRun
    ) -> Dict[str, Any]:
        """
        Execute a single pipeline step with retry logic.
        
        **Validates: Requirement 3.1** - Handle retry policies for failed steps.
        **Validates: Requirement 3.8** - Emit step telemetry to Langfuse
        """
        step_exec = StepExecution(step_name=step.name, status=StepStatus.RUNNING)
        run.step_executions.append(step_exec)

        logger.info(f"Executing step '{step.name}' (agent={step.agent})")

        attempt = 0
        last_error = None
        span = None

        while attempt <= step.retry_policy.max_retries:
            try:
                step_exec.attempt = attempt + 1
                step_exec.start_time = datetime.utcnow()

                # Prepare step inputs
                step_inputs = {key: artifacts.get(key) for key in step.inputs}

                # Start telemetry span
                span = self._telemetry.trace_step_start(
                    run_id=run.id,
                    step_name=step.name,
                    agent=step.agent,
                    inputs=step_inputs,
                    attempt=attempt + 1,
                )

                # Execute step function with timeout
                if step.function:
                    if step.timeout:
                        result = await asyncio.wait_for(
                            step.function(**step_inputs), timeout=step.timeout
                        )
                    else:
                        result = await step.function(**step_inputs)
                else:
                    # Placeholder for when function is not provided
                    result = {}

                # Record success
                step_exec.status = StepStatus.COMPLETED
                step_exec.end_time = datetime.utcnow()
                step_exec.duration = (
                    step_exec.end_time - step_exec.start_time
                ).total_seconds()
                step_exec.outputs = result

                # End telemetry span
                if span:
                    self._telemetry.trace_step_end(
                        span_id=span.id if hasattr(span, 'id') else str(span),
                        status="completed",
                        outputs=result,
                        duration=step_exec.duration,
                    )

                # Record step duration metric
                self._telemetry.record_metric(
                    "pipeline.step.duration",
                    step_exec.duration,
                    tags={
                        "step": step.name,
                        "agent": step.agent,
                        "status": "completed",
                    },
                )

                logger.info(
                    f"Step '{step.name}' completed in {step_exec.duration:.2f}s"
                )

                return result

            except Exception as e:
                last_error = e
                attempt += 1

                logger.warning(
                    f"Step '{step.name}' failed (attempt {attempt}/{step.retry_policy.max_retries + 1}): {e}"
                )

                # Capture error in telemetry
                self._telemetry.capture_error(
                    e,
                    context={
                        "step": step.name,
                        "agent": step.agent,
                        "attempt": attempt,
                        "run_id": run.id,
                    },
                    level="warning" if attempt <= step.retry_policy.max_retries else "error",
                )

                if attempt <= step.retry_policy.max_retries:
                    # Calculate delay with exponential backoff
                    if step.retry_policy.exponential_backoff:
                        delay = min(
                            step.retry_policy.initial_delay * (2 ** (attempt - 1)),
                            step.retry_policy.max_delay,
                        )
                    else:
                        delay = step.retry_policy.initial_delay

                    logger.info(f"Retrying step '{step.name}' in {delay:.1f}s...")
                    await asyncio.sleep(delay)

        # All retries exhausted
        step_exec.status = StepStatus.FAILED
        step_exec.error = str(last_error)
        step_exec.end_time = datetime.utcnow()
        step_exec.duration = (
            step_exec.end_time - step_exec.start_time
        ).total_seconds()

        # End telemetry span with error
        if span:
            self._telemetry.trace_step_end(
                span_id=span.id if hasattr(span, 'id') else str(span),
                status="failed",
                error=str(last_error),
                duration=step_exec.duration,
            )

        # Record failure metric
        self._telemetry.record_metric(
            "pipeline.step.duration",
            step_exec.duration,
            tags={
                "step": step.name,
                "agent": step.agent,
                "status": "failed",
            },
        )

        raise RuntimeError(
            f"Step '{step.name}' failed after {attempt} attempts: {last_error}"
        )

    def get_run(self, run_id: str) -> Optional[PipelineRun]:
        """Get a pipeline run by ID."""
        return self._runs.get(run_id)

    def list_runs(
        self, pipeline_name: Optional[str] = None, limit: int = 100
    ) -> List[PipelineRun]:
        """
        List pipeline runs, optionally filtered by pipeline name.
        
        **Validates: Requirement 3.6** - Provide monitoring of pipeline execution.
        """
        runs = list(self._runs.values())
        if pipeline_name:
            runs = [r for r in runs if r.pipeline_name == pipeline_name]
        # Sort by start time, most recent first
        runs.sort(key=lambda r: r.start_time or datetime.min, reverse=True)
        return runs[:limit]

    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a running pipeline."""
        run = self._runs.get(run_id)
        if run and run.status == PipelineStatus.RUNNING:
            run.status = PipelineStatus.CANCELLED
            run.end_time = datetime.utcnow()
            if run.start_time:
                run.duration = (run.end_time - run.start_time).total_seconds()
            logger.info(f"Pipeline run {run_id} cancelled")
            return True
        return False
