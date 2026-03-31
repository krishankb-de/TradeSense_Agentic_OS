"""
Workflow templates for TradeSense agent orchestration.

Provides pre-configured pipeline templates for common workflows:
- Intake: Lead capture and triage
- Diagnostic: Issue analysis and parts sourcing
- Fulfillment: Job completion and scheduling

**Validates: Requirements 3.1, 3.3**
"""

import logging
from typing import Any, Dict, Optional

from orchestration.pipeline import Pipeline, PipelineStep, RetryPolicy

logger = logging.getLogger(__name__)


class WorkflowTemplate:
    """Base class for workflow templates."""

    @staticmethod
    def create_pipeline(name: str, description: str = "") -> Pipeline:
        """Create a new pipeline with common configuration."""
        return Pipeline(name=name, description=description, enable_cache=False)


class IntakeWorkflow(WorkflowTemplate):
    """
    Intake workflow for lead capture and triage.
    
    This workflow handles:
    1. Voice/SMS input processing
    2. Lead information extraction
    3. Urgency classification
    4. Parts availability check
    5. Technician assignment
    
    **Validates: Requirement 3.1** - Coordinate intake agent execution.
    """

    @staticmethod
    def create() -> Pipeline:
        """Create intake workflow pipeline."""
        pipeline = WorkflowTemplate.create_pipeline(
            name="intake_workflow",
            description="Lead capture and triage workflow",
        )

        # Step 1: Process input and extract lead information
        pipeline.add_step(
            PipelineStep(
                name="extract_lead_info",
                agent="intake",
                inputs=["raw_input", "source"],
                outputs=["lead_data"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=1.0),
                timeout=30.0,
            )
        )

        # Step 2: Classify urgency and service type
        pipeline.add_step(
            PipelineStep(
                name="classify_urgency",
                agent="intake",
                inputs=["lead_data"],
                outputs=["triage_result"],
                depends_on=["extract_lead_info"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=1.0),
                timeout=15.0,
            )
        )

        # Step 3: Check parts availability
        pipeline.add_step(
            PipelineStep(
                name="check_parts",
                agent="intake",
                inputs=["triage_result"],
                outputs=["parts_availability"],
                depends_on=["classify_urgency"],
                retry_policy=RetryPolicy(max_retries=3, initial_delay=2.0),
                timeout=20.0,
            )
        )

        # Step 4: Assign technician
        pipeline.add_step(
            PipelineStep(
                name="assign_technician",
                agent="intake",
                inputs=["triage_result", "parts_availability"],
                outputs=["assignment"],
                depends_on=["classify_urgency", "check_parts"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=1.0),
                timeout=10.0,
            )
        )

        # Step 5: Create lead record
        pipeline.add_step(
            PipelineStep(
                name="create_lead",
                agent="intake",
                inputs=["lead_data", "triage_result", "assignment"],
                outputs=["lead_id"],
                depends_on=["extract_lead_info", "classify_urgency", "assign_technician"],
                retry_policy=RetryPolicy(max_retries=3, initial_delay=2.0),
                timeout=10.0,
            )
        )

        logger.info("Created intake workflow pipeline with 5 steps")
        return pipeline


class DiagnosticWorkflow(WorkflowTemplate):
    """
    Diagnostic workflow for issue analysis and parts sourcing.
    
    This workflow handles:
    1. Issue description analysis
    2. Equipment image parsing (if provided)
    3. Root cause diagnosis
    4. Parts recommendation with alternatives
    5. Repair guide generation
    
    **Validates: Requirement 3.1** - Coordinate diagnostic agent execution.
    """

    @staticmethod
    def create() -> Pipeline:
        """Create diagnostic workflow pipeline."""
        pipeline = WorkflowTemplate.create_pipeline(
            name="diagnostic_workflow",
            description="Issue analysis and parts sourcing workflow",
        )

        # Step 1: Analyze issue description
        pipeline.add_step(
            PipelineStep(
                name="analyze_issue",
                agent="diagnostic",
                inputs=["issue_description", "equipment_info"],
                outputs=["initial_diagnosis"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=2.0),
                timeout=30.0,
            )
        )

        # Step 2: Parse equipment image (optional)
        pipeline.add_step(
            PipelineStep(
                name="parse_equipment_image",
                agent="diagnostic",
                inputs=["equipment_image"],
                outputs=["equipment_details"],
                depends_on=[],  # Can run in parallel with analyze_issue
                retry_policy=RetryPolicy(max_retries=2, initial_delay=1.0),
                timeout=20.0,
            )
        )

        # Step 3: Generate detailed diagnosis
        pipeline.add_step(
            PipelineStep(
                name="generate_diagnosis",
                agent="diagnostic",
                inputs=["initial_diagnosis", "equipment_details"],
                outputs=["diagnosis"],
                depends_on=["analyze_issue", "parse_equipment_image"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=2.0),
                timeout=45.0,
            )
        )

        # Step 4: Find required parts
        pipeline.add_step(
            PipelineStep(
                name="find_parts",
                agent="diagnostic",
                inputs=["diagnosis"],
                outputs=["parts_recommendation"],
                depends_on=["generate_diagnosis"],
                retry_policy=RetryPolicy(max_retries=3, initial_delay=2.0),
                timeout=30.0,
            )
        )

        # Step 5: Generate repair guide
        pipeline.add_step(
            PipelineStep(
                name="generate_repair_guide",
                agent="diagnostic",
                inputs=["diagnosis", "parts_recommendation"],
                outputs=["repair_guide"],
                depends_on=["generate_diagnosis", "find_parts"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=1.0),
                timeout=20.0,
            )
        )

        logger.info("Created diagnostic workflow pipeline with 5 steps")
        return pipeline


class FulfillmentWorkflow(WorkflowTemplate):
    """
    Fulfillment workflow for job completion and scheduling.
    
    This workflow handles:
    1. Schedule optimization
    2. Job completion logging
    3. Carbon footprint calculation
    4. Invoice generation
    5. Customer notification
    
    **Validates: Requirement 3.1** - Coordinate fulfillment agent execution.
    """

    @staticmethod
    def create() -> Pipeline:
        """Create fulfillment workflow pipeline."""
        pipeline = WorkflowTemplate.create_pipeline(
            name="fulfillment_workflow",
            description="Job completion and scheduling workflow",
        )

        # Step 1: Optimize schedule
        pipeline.add_step(
            PipelineStep(
                name="optimize_schedule",
                agent="fulfillment",
                inputs=["jobs", "technicians", "constraints"],
                outputs=["schedule"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=2.0),
                timeout=60.0,
            )
        )

        # Step 2: Log job completion
        pipeline.add_step(
            PipelineStep(
                name="log_completion",
                agent="fulfillment",
                inputs=["job_id", "completion_details"],
                outputs=["job_record"],
                retry_policy=RetryPolicy(max_retries=3, initial_delay=2.0),
                timeout=15.0,
            )
        )

        # Step 3: Calculate carbon footprint
        pipeline.add_step(
            PipelineStep(
                name="calculate_carbon",
                agent="fulfillment",
                inputs=["job_record"],
                outputs=["carbon_footprint"],
                depends_on=["log_completion"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=1.0),
                timeout=20.0,
            )
        )

        # Step 4: Generate invoice
        pipeline.add_step(
            PipelineStep(
                name="generate_invoice",
                agent="fulfillment",
                inputs=["job_record", "carbon_footprint"],
                outputs=["invoice"],
                depends_on=["log_completion", "calculate_carbon"],
                retry_policy=RetryPolicy(max_retries=3, initial_delay=2.0),
                timeout=15.0,
            )
        )

        # Step 5: Send customer notification
        pipeline.add_step(
            PipelineStep(
                name="notify_customer",
                agent="fulfillment",
                inputs=["invoice", "job_record"],
                outputs=["notification_status"],
                depends_on=["generate_invoice"],
                retry_policy=RetryPolicy(max_retries=3, initial_delay=5.0),
                timeout=30.0,
            )
        )

        logger.info("Created fulfillment workflow pipeline with 5 steps")
        return pipeline


class CompositeWorkflow(WorkflowTemplate):
    """
    Composite workflow that chains intake -> diagnostic -> fulfillment.
    
    This represents a complete end-to-end job flow from initial contact
    to completion.
    """

    @staticmethod
    def create() -> Pipeline:
        """Create composite workflow pipeline."""
        pipeline = WorkflowTemplate.create_pipeline(
            name="composite_workflow",
            description="End-to-end job workflow from intake to fulfillment",
        )

        # Phase 1: Intake
        pipeline.add_step(
            PipelineStep(
                name="intake_phase",
                agent="intake",
                inputs=["raw_input", "source"],
                outputs=["lead_id", "triage_result"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=2.0),
                timeout=60.0,
            )
        )

        # Phase 2: Diagnostic
        pipeline.add_step(
            PipelineStep(
                name="diagnostic_phase",
                agent="diagnostic",
                inputs=["triage_result", "equipment_image"],
                outputs=["diagnosis", "parts_recommendation"],
                depends_on=["intake_phase"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=2.0),
                timeout=120.0,
            )
        )

        # Phase 3: Fulfillment
        pipeline.add_step(
            PipelineStep(
                name="fulfillment_phase",
                agent="fulfillment",
                inputs=["lead_id", "diagnosis", "parts_recommendation"],
                outputs=["job_id", "schedule", "invoice"],
                depends_on=["diagnostic_phase"],
                retry_policy=RetryPolicy(max_retries=2, initial_delay=2.0),
                timeout=90.0,
            )
        )

        logger.info("Created composite workflow pipeline with 3 phases")
        return pipeline


# Workflow registry for easy access
WORKFLOW_REGISTRY: Dict[str, type[WorkflowTemplate]] = {
    "intake": IntakeWorkflow,
    "diagnostic": DiagnosticWorkflow,
    "fulfillment": FulfillmentWorkflow,
    "composite": CompositeWorkflow,
}


def get_workflow(workflow_type: str) -> Optional[Pipeline]:
    """
    Get a workflow pipeline by type.
    
    Args:
        workflow_type: One of 'intake', 'diagnostic', 'fulfillment', 'composite'
    
    Returns:
        Pipeline instance or None if workflow type not found
    """
    workflow_class = WORKFLOW_REGISTRY.get(workflow_type)
    if workflow_class:
        return workflow_class.create()
    logger.warning(f"Unknown workflow type: {workflow_type}")
    return None
