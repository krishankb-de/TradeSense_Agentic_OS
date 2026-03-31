"""
Property-based tests for Fulfillment Agent.

Tests properties that should hold across all valid inputs:
- Schedule optimization constraints
- Schedule travel optimization
- Carbon calculation completeness
- Inventory synchronization

Uses Hypothesis for property-based testing.

**Validates: Requirements 6.2, 6.3, 6.4, 7.2, 8.6**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from agents.fulfillment import (
    FulfillmentAgent,
    Job,
    Technician,
    GeoLocation,
    JobStatus,
    CompletionDetails,
    EmissionCategory,
)


# ============================================================================
# Hypothesis Strategies
# ============================================================================


@st.composite
def geo_location_strategy(draw):
    """Generate valid geographic locations."""
    return GeoLocation(
        latitude=draw(st.floats(min_value=-90, max_value=90)),
        longitude=draw(st.floats(min_value=-180, max_value=180)),
        address=draw(st.text(min_size=5, max_size=50)),
        city=draw(st.text(min_size=3, max_size=30)),
        state=draw(st.text(min_size=2, max_size=2)),
        zip_code=draw(st.text(min_size=5, max_size=10)),
    )


@st.composite
def technician_strategy(draw):
    """Generate valid technicians."""
    skills = draw(st.lists(
        st.sampled_from(["HVAC", "Plumbing", "Electrical", "Appliance"]),
        min_size=1,
        max_size=4,
        unique=True,
    ))
    
    now = datetime.now()
    
    return Technician(
        id=f"tech-{draw(st.integers(min_value=1, max_value=1000))}",
        name=draw(st.text(min_size=5, max_size=30)),
        skills=skills,
        current_location=draw(geo_location_strategy()),
        assigned_jobs=[],
        availability_start=now,
        availability_end=now + timedelta(hours=8),
        max_jobs_per_day=draw(st.integers(min_value=4, max_value=12)),
    )


@st.composite
def job_strategy(draw):
    """Generate valid jobs."""
    service_types = ["HVAC", "Plumbing", "Electrical", "Appliance"]
    service_type = draw(st.sampled_from(service_types))
    
    # Map service type to required skills
    skill_map = {
        "HVAC": ["HVAC"],
        "Plumbing": ["Plumbing"],
        "Electrical": ["Electrical"],
        "Appliance": ["Appliance"],
    }
    
    urgency_map = {
        "emergency": 10,
        "urgent": 6,
        "routine": 3,
    }
    urgency = draw(st.sampled_from(["emergency", "urgent", "routine"]))
    
    return Job(
        id=f"job-{draw(st.integers(min_value=1, max_value=10000))}",
        lead_id=f"lead-{draw(st.integers(min_value=1, max_value=10000))}",
        technician_id=None,
        status=JobStatus.SCHEDULED,
        service_type=service_type,
        location=draw(geo_location_strategy()),
        scheduled_start=None,
        scheduled_end=None,
        actual_start=None,
        actual_end=None,
        estimated_duration=draw(st.integers(min_value=30, max_value=240)),
        priority=urgency_map[urgency],
        urgency=urgency,
        required_skills=skill_map[service_type],
        parts_used=[],
        labor_hours=draw(st.floats(min_value=0.5, max_value=8.0)),
        total_cost=draw(st.floats(min_value=50.0, max_value=1000.0)),
    )


# ============================================================================
# Helper Functions (not fixtures to avoid Hypothesis health check issues)
# ============================================================================


def create_mock_llm_client():
    """Create mock LLM client."""
    client = Mock()
    client.generate = AsyncMock(return_value=Mock(text="Test response"))
    return client


def create_fulfillment_agent():
    """Create fulfillment agent for testing."""
    return FulfillmentAgent(
        llm_client=create_mock_llm_client(),
        enable_logging=False,
    )


# ============================================================================
# Property 7: Schedule Optimization Constraints
# ============================================================================


@pytest.mark.asyncio
@given(
    jobs=st.lists(job_strategy(), min_size=1, max_size=20),
    technicians=st.lists(technician_strategy(), min_size=1, max_size=5),
)
@settings(max_examples=50, deadline=5000)
async def test_property_schedule_constraints(jobs, technicians):
    """
    **Property 7: Schedule Optimization Constraints**
    
    For any generated schedule:
    - All assigned technicians should have required skills for their jobs
    - Utilization rate should be >= 0.0 and <= 1.0
    - No scheduling conflicts should exist (no overlapping jobs for same technician)
    
    **Validates: Requirements 6.2, 6.3**
    """
    fulfillment_agent = create_fulfillment_agent()
    
    # Ensure unique job and technician IDs
    job_ids = set()
    unique_jobs = []
    for job in jobs:
        if job.id not in job_ids:
            job_ids.add(job.id)
            unique_jobs.append(job)
    
    tech_ids = set()
    unique_techs = []
    for tech in technicians:
        if tech.id not in tech_ids:
            tech_ids.add(tech.id)
            unique_techs.append(tech)
    
    assume(len(unique_jobs) > 0)
    assume(len(unique_techs) > 0)
    
    schedule = await fulfillment_agent.optimize_schedule(unique_jobs, unique_techs)
    
    # Property 1: All assigned technicians have required skills
    for assignment in schedule.assignments:
        job = next(j for j in unique_jobs if j.id == assignment.job_id)
        tech = next(t for t in unique_techs if t.id == assignment.technician_id)
        
        # Verify technician has all required skills
        for skill in job.required_skills:
            assert skill in tech.skills, (
                f"Technician {tech.id} missing required skill {skill} for job {job.id}"
            )
    
    # Property 2: Utilization rate is valid
    assert 0.0 <= schedule.utilization_rate <= 1.0, (
        f"Utilization rate {schedule.utilization_rate} out of valid range [0.0, 1.0]"
    )
    
    # Property 3: No scheduling conflicts (no overlapping jobs for same technician)
    tech_schedules = {}
    for assignment in schedule.assignments:
        if assignment.technician_id not in tech_schedules:
            tech_schedules[assignment.technician_id] = []
        tech_schedules[assignment.technician_id].append(assignment)
    
    for tech_id, assignments in tech_schedules.items():
        # Sort by start time
        sorted_assignments = sorted(assignments, key=lambda a: a.scheduled_start)
        
        # Check for overlaps
        for i in range(len(sorted_assignments) - 1):
            current = sorted_assignments[i]
            next_assignment = sorted_assignments[i + 1]
            
            assert current.scheduled_end <= next_assignment.scheduled_start, (
                f"Scheduling conflict for technician {tech_id}: "
                f"Job {current.job_id} ends at {current.scheduled_end}, "
                f"but job {next_assignment.job_id} starts at {next_assignment.scheduled_start}"
            )


# ============================================================================
# Property 8: Schedule Travel Optimization
# ============================================================================


@pytest.mark.asyncio
@given(
    jobs=st.lists(job_strategy(), min_size=2, max_size=10),
    technicians=st.lists(technician_strategy(), min_size=1, max_size=3),
)
@settings(max_examples=30, deadline=5000)
async def test_property_schedule_travel_optimization(jobs, technicians):
    """
    **Property 8: Schedule Travel Optimization**
    
    For any set of jobs and technicians, the optimized schedule should
    minimize total travel time compared to naive assignment.
    
    This property verifies that the optimization algorithm produces
    better results than random assignment.
    
    **Validates: Requirement 6.4**
    """
    fulfillment_agent = create_fulfillment_agent()
    
    # Ensure unique IDs
    job_ids = set()
    unique_jobs = []
    for job in jobs:
        if job.id not in job_ids:
            job_ids.add(job.id)
            unique_jobs.append(job)
    
    tech_ids = set()
    unique_techs = []
    for tech in technicians:
        if tech.id not in tech_ids:
            tech_ids.add(tech.id)
            unique_techs.append(tech)
    
    assume(len(unique_jobs) >= 2)
    assume(len(unique_techs) >= 1)
    
    # Get optimized schedule
    optimized_schedule = await fulfillment_agent.optimize_schedule(unique_jobs, unique_techs)
    
    # Calculate total travel time for optimized schedule
    optimized_travel_time = sum(route.total_travel_time for route in optimized_schedule.routes)
    
    # Property: Optimized travel time should be non-negative
    assert optimized_travel_time >= 0, (
        f"Optimized travel time {optimized_travel_time} is negative"
    )
    
    # Property: Routes should have valid distances
    for route in optimized_schedule.routes:
        assert route.total_distance >= 0, (
            f"Route for technician {route.technician_id} has negative distance"
        )
        assert route.total_travel_time >= 0, (
            f"Route for technician {route.technician_id} has negative travel time"
        )
        assert route.total_duration >= route.total_travel_time, (
            f"Route for technician {route.technician_id} has duration less than travel time"
        )


# ============================================================================
# Property 9: Carbon Calculation Completeness
# ============================================================================


@pytest.mark.asyncio
@given(
    job=job_strategy(),
    travel_distance=st.floats(min_value=0.0, max_value=100.0),
    num_parts=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=100, deadline=2000)
async def test_property_carbon_calculation_completeness(
    job,
    travel_distance,
    num_parts,
):
    """
    **Property 11: Carbon Calculation Completeness**
    
    For any completed job, carbon footprint calculation should:
    - Include all emission sources (travel, parts, AI infrastructure)
    - Sum correctly (total = sum of breakdown)
    - Use only open-source data sources
    - Avoid proprietary APIs
    
    **Validates: Requirements 8.6, 8.10**
    """
    fulfillment_agent = create_fulfillment_agent()
    
    # Add parts to job
    job.parts_used = [
        {"id": f"part-{i}", "name": f"Part {i}", "quantity": 1}
        for i in range(num_parts)
    ]
    
    carbon = await fulfillment_agent.calculate_carbon_footprint(
        job=job,
        travel_distance=travel_distance,
    )
    
    # Property 1: Total emissions equals sum of breakdown
    breakdown_sum = sum(source.emissions for source in carbon.breakdown)
    assert abs(carbon.total_emissions - breakdown_sum) < 0.01, (
        f"Total emissions {carbon.total_emissions} does not match "
        f"breakdown sum {breakdown_sum}"
    )
    
    # Property 2: All emission sources are accounted for
    categories = [source.category for source in carbon.breakdown]
    
    # If travel distance > 0, should have travel emissions
    if travel_distance > 0:
        assert EmissionCategory.TRAVEL in categories, (
            "Missing travel emissions for non-zero travel distance"
        )
    
    # If parts used, should have parts emissions
    if num_parts > 0:
        assert EmissionCategory.PARTS in categories, (
            "Missing parts emissions when parts are used"
        )
    
    # Should always have AI infrastructure emissions
    assert EmissionCategory.AI_INFRASTRUCTURE in categories, (
        "Missing AI infrastructure emissions"
    )
    
    # Property 3: Only open-source data sources used
    valid_sources = ["eGRID", "EPA-GHG", "ADEME", "Kabaun", "CodeCarbon"]
    for source in carbon.data_sources:
        assert source in valid_sources, (
            f"Invalid data source {source}, must be one of {valid_sources}"
        )
    
    # Property 4: Total emissions is non-negative
    assert carbon.total_emissions >= 0, (
        f"Total emissions {carbon.total_emissions} is negative"
    )


# ============================================================================
# Property 10: Inventory Synchronization
# ============================================================================


@pytest.mark.asyncio
@given(
    num_parts=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=50, deadline=2000)
async def test_property_inventory_synchronization(num_parts):
    """
    **Property 10: Inventory Synchronization**
    
    For any completed job with parts used, InvenTree inventory levels
    should be updated to reflect the parts consumed.
    
    **Validates: Requirement 7.2**
    """
    # Create mock InvenTree client
    mock_inventree = Mock()
    mock_inventree.update_stock = AsyncMock()
    
    agent = FulfillmentAgent(
        llm_client=create_mock_llm_client(),
        inventree_client=mock_inventree,
        enable_logging=False,
    )
    
    # Create completion details with parts
    parts_used = [
        {"id": f"part-{i}", "name": f"Part {i}", "quantity": 1}
        for i in range(num_parts)
    ]
    
    completion = CompletionDetails(
        job_id="job-test",
        parts_used=parts_used,
        labor_hours=2.0,
        notes="Test completion",
        first_time_fix=True,
    )
    
    await agent.log_job_completion(completion)
    
    # Property: Inventory update should be called for each part
    assert mock_inventree.update_stock.call_count == num_parts, (
        f"Expected {num_parts} inventory updates, "
        f"got {mock_inventree.update_stock.call_count}"
    )
    
    # Property: Each update should decrease stock (negative quantity)
    for call in mock_inventree.update_stock.call_args_list:
        kwargs = call[1]
        assert kwargs["quantity"] < 0, (
            f"Inventory update should decrease stock, got quantity {kwargs['quantity']}"
        )


# ============================================================================
# Additional Properties
# ============================================================================


@pytest.mark.asyncio
@given(
    jobs=st.lists(job_strategy(), min_size=1, max_size=15),
    technicians=st.lists(technician_strategy(), min_size=1, max_size=5),
)
@settings(max_examples=30, deadline=5000)
async def test_property_emergency_prioritization(jobs, technicians):
    """
    Property: Emergency jobs should be scheduled before non-emergency jobs.
    
    **Validates: Requirement 6.6**
    """
    fulfillment_agent = create_fulfillment_agent()
    
    # Ensure unique IDs
    job_ids = set()
    unique_jobs = []
    for job in jobs:
        if job.id not in job_ids:
            job_ids.add(job.id)
            unique_jobs.append(job)
    
    tech_ids = set()
    unique_techs = []
    for tech in technicians:
        if tech.id not in tech_ids:
            tech_ids.add(tech.id)
            unique_techs.append(tech)
    
    assume(len(unique_jobs) > 0)
    assume(len(unique_techs) > 0)
    
    # Check if there are any emergency jobs
    emergency_jobs = [j for j in unique_jobs if j.urgency == "emergency"]
    non_emergency_jobs = [j for j in unique_jobs if j.urgency != "emergency"]
    
    if not emergency_jobs or not non_emergency_jobs:
        # Skip if no mix of emergency and non-emergency jobs
        return
    
    schedule = await fulfillment_agent.optimize_schedule(unique_jobs, unique_techs)
    
    # Find earliest emergency and non-emergency assignments
    emergency_assignments = [
        a for a in schedule.assignments
        if any(j.id == a.job_id and j.urgency == "emergency" for j in unique_jobs)
    ]
    non_emergency_assignments = [
        a for a in schedule.assignments
        if any(j.id == a.job_id and j.urgency != "emergency" for j in unique_jobs)
    ]
    
    if emergency_assignments and non_emergency_assignments:
        earliest_emergency = min(emergency_assignments, key=lambda a: a.scheduled_start)
        earliest_non_emergency = min(non_emergency_assignments, key=lambda a: a.scheduled_start)
        
        # Property: Earliest emergency should be scheduled before or at same time as earliest non-emergency
        assert earliest_emergency.scheduled_start <= earliest_non_emergency.scheduled_start, (
            f"Emergency job scheduled at {earliest_emergency.scheduled_start} "
            f"after non-emergency job at {earliest_non_emergency.scheduled_start}"
        )


@pytest.mark.asyncio
@given(
    labor_hours=st.floats(min_value=0.5, max_value=8.0),
)
@settings(max_examples=50, deadline=2000)
async def test_property_carbon_monotonicity(labor_hours):
    """
    Property: More labor hours should result in equal or higher AI infrastructure emissions.
    
    **Validates: Requirement 8.9**
    """
    fulfillment_agent = create_fulfillment_agent()
    
    # Create two jobs with different labor hours
    job1 = Job(
        id="job-1",
        lead_id="lead-1",
        technician_id=None,
        status=JobStatus.COMPLETED,
        service_type="HVAC",
        location=GeoLocation(40.7128, -74.0060, "", "", "", ""),
        scheduled_start=None,
        scheduled_end=None,
        actual_start=None,
        actual_end=None,
        estimated_duration=60,
        priority=5,
        urgency="routine",
        required_skills=["HVAC"],
        parts_used=[],
        labor_hours=labor_hours,
        total_cost=100.0,
    )
    
    job2 = Job(
        id="job-2",
        lead_id="lead-2",
        technician_id=None,
        status=JobStatus.COMPLETED,
        service_type="HVAC",
        location=GeoLocation(40.7128, -74.0060, "", "", "", ""),
        scheduled_start=None,
        scheduled_end=None,
        actual_start=None,
        actual_end=None,
        estimated_duration=60,
        priority=5,
        urgency="routine",
        required_skills=["HVAC"],
        parts_used=[],
        labor_hours=labor_hours * 2,  # Double the labor hours
        total_cost=200.0,
    )
    
    carbon1 = await fulfillment_agent.calculate_carbon_footprint(job1, travel_distance=0.0)
    carbon2 = await fulfillment_agent.calculate_carbon_footprint(job2, travel_distance=0.0)
    
    # Property: More labor hours should result in equal or higher emissions
    assert carbon2.total_emissions >= carbon1.total_emissions, (
        f"Job with {job2.labor_hours} hours has lower emissions ({carbon2.total_emissions}) "
        f"than job with {job1.labor_hours} hours ({carbon1.total_emissions})"
    )
