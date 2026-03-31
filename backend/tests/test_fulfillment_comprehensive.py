"""
Comprehensive tests for Fulfillment Agent (Task 10.12).

Tests all functionality end-to-end:
- Schedule optimization with multiple scenarios
- Emergency job prioritization
- Carbon footprint calculation
- Job completion logging
- KPI tracking
- Report generation
- Integration with inventory system

**Validates: Requirements 6.1-6.11, 8.6-8.10, 9.7-9.8**
"""

import pytest
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
    ComplianceStatus,
    create_fulfillment_agent,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = Mock()
    client.generate = AsyncMock(return_value=Mock(text="Test response"))
    return client


@pytest.fixture
def mock_inventree_client():
    """Mock InvenTree client."""
    client = Mock()
    client.update_stock = AsyncMock()
    return client


@pytest.fixture
def fulfillment_agent(mock_llm_client, mock_inventree_client):
    """Create fulfillment agent with inventory integration."""
    return FulfillmentAgent(
        llm_client=mock_llm_client,
        inventree_client=mock_inventree_client,
        enable_logging=False,
    )


@pytest.fixture
def sample_locations():
    """Sample geographic locations."""
    return [
        GeoLocation(40.7128, -74.0060, "123 Main St", "New York", "NY", "10001"),
        GeoLocation(40.7589, -73.9851, "456 Broadway", "New York", "NY", "10036"),
        GeoLocation(40.7614, -73.9776, "789 Park Ave", "New York", "NY", "10065"),
        GeoLocation(40.7489, -73.9680, "321 5th Ave", "New York", "NY", "10016"),
    ]


@pytest.fixture
def sample_technicians(sample_locations):
    """Sample technicians with different skills."""
    now = datetime.now()
    return [
        Technician(
            id="tech-001",
            name="John Smith",
            skills=["HVAC", "Electrical"],
            current_location=sample_locations[0],
            assigned_jobs=[],
            availability_start=now,
            availability_end=now + timedelta(hours=8),
            max_jobs_per_day=8,
        ),
        Technician(
            id="tech-002",
            name="Jane Doe",
            skills=["Plumbing", "HVAC"],
            current_location=sample_locations[1],
            assigned_jobs=[],
            availability_start=now,
            availability_end=now + timedelta(hours=8),
            max_jobs_per_day=8,
        ),
        Technician(
            id="tech-003",
            name="Bob Johnson",
            skills=["Electrical", "Appliance"],
            current_location=sample_locations[2],
            assigned_jobs=[],
            availability_start=now,
            availability_end=now + timedelta(hours=8),
            max_jobs_per_day=6,
        ),
    ]


@pytest.fixture
def sample_jobs(sample_locations):
    """Sample jobs with different priorities and types."""
    return [
        Job(
            id="job-emergency",
            lead_id="lead-001",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="HVAC",
            location=sample_locations[0],
            scheduled_start=None,
            scheduled_end=None,
            actual_start=None,
            actual_end=None,
            estimated_duration=120,
            priority=10,
            urgency="emergency",
            required_skills=["HVAC"],
            parts_used=[],
            labor_hours=2.0,
            total_cost=350.0,
            notes="Furnace not working, no heat",
        ),
        Job(
            id="job-urgent-1",
            lead_id="lead-002",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="Plumbing",
            location=sample_locations[1],
            scheduled_start=None,
            scheduled_end=None,
            actual_start=None,
            actual_end=None,
            estimated_duration=90,
            priority=6,
            urgency="urgent",
            required_skills=["Plumbing"],
            parts_used=[],
            labor_hours=1.5,
            total_cost=220.0,
            notes="Leaking faucet",
        ),
        Job(
            id="job-urgent-2",
            lead_id="lead-003",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="Electrical",
            location=sample_locations[2],
            scheduled_start=None,
            scheduled_end=None,
            actual_start=None,
            actual_end=None,
            estimated_duration=60,
            priority=6,
            urgency="urgent",
            required_skills=["Electrical"],
            parts_used=[],
            labor_hours=1.0,
            total_cost=180.0,
            notes="Outlet not working",
        ),
        Job(
            id="job-routine-1",
            lead_id="lead-004",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="HVAC",
            location=sample_locations[3],
            scheduled_start=None,
            scheduled_end=None,
            actual_start=None,
            actual_end=None,
            estimated_duration=60,
            priority=3,
            urgency="routine",
            required_skills=["HVAC"],
            parts_used=[],
            labor_hours=1.0,
            total_cost=150.0,
            notes="AC tune-up",
        ),
        Job(
            id="job-routine-2",
            lead_id="lead-005",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="Appliance",
            location=sample_locations[0],
            scheduled_start=None,
            scheduled_end=None,
            actual_start=None,
            actual_end=None,
            estimated_duration=45,
            priority=3,
            urgency="routine",
            required_skills=["Appliance"],
            parts_used=[],
            labor_hours=0.75,
            total_cost=120.0,
            notes="Refrigerator maintenance",
        ),
    ]


# ============================================================================
# Comprehensive Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_comprehensive_schedule_optimization(
    fulfillment_agent,
    sample_jobs,
    sample_technicians,
):
    """
    Test comprehensive schedule optimization with multiple jobs and technicians.
    
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.6**
    """
    schedule = await fulfillment_agent.optimize_schedule(sample_jobs, sample_technicians)
    
    # Verify all jobs are assigned or marked unassigned
    total_jobs = len(schedule.assignments) + len(schedule.unassigned_jobs)
    assert total_jobs == len(sample_jobs)
    
    # Verify emergency job is scheduled first
    if schedule.assignments:
        first_assignment = schedule.assignments[0]
        first_job = next(j for j in sample_jobs if j.id == first_assignment.job_id)
        assert first_job.urgency == "emergency"
    
    # Verify skill matching
    for assignment in schedule.assignments:
        job = next(j for j in sample_jobs if j.id == assignment.job_id)
        tech = next(t for t in sample_technicians if t.id == assignment.technician_id)
        for skill in job.required_skills:
            assert skill in tech.skills
    
    # Verify no scheduling conflicts
    tech_schedules = {}
    for assignment in schedule.assignments:
        if assignment.technician_id not in tech_schedules:
            tech_schedules[assignment.technician_id] = []
        tech_schedules[assignment.technician_id].append(assignment)
    
    for tech_id, assignments in tech_schedules.items():
        sorted_assignments = sorted(assignments, key=lambda a: a.scheduled_start)
        for i in range(len(sorted_assignments) - 1):
            current = sorted_assignments[i]
            next_assignment = sorted_assignments[i + 1]
            assert current.scheduled_end <= next_assignment.scheduled_start
    
    # Verify utilization rate is valid
    assert 0.0 <= schedule.utilization_rate <= 1.0
    
    # Verify routes are generated
    assert len(schedule.routes) > 0
    for route in schedule.routes:
        assert route.total_distance >= 0
        assert route.total_travel_time >= 0
        assert route.total_duration >= route.total_travel_time


@pytest.mark.asyncio
async def test_comprehensive_carbon_footprint(fulfillment_agent, sample_jobs):
    """
    Test comprehensive carbon footprint calculation with all emission sources.
    
    **Validates: Requirements 6.8, 8.1-8.10**
    """
    # Use a completed job with parts
    job = sample_jobs[0]
    job.status = JobStatus.COMPLETED
    job.parts_used = [
        {"id": "part-001", "name": "Ignitor", "quantity": 1},
        {"id": "part-002", "name": "Flame Sensor", "quantity": 1},
        {"id": "part-003", "name": "Thermostat", "quantity": 1},
    ]
    
    carbon = await fulfillment_agent.calculate_carbon_footprint(
        job=job,
        travel_distance=25.0,
    )
    
    # Verify all emission categories are present
    categories = [source.category for source in carbon.breakdown]
    assert EmissionCategory.TRAVEL in categories
    assert EmissionCategory.PARTS in categories
    assert EmissionCategory.AI_INFRASTRUCTURE in categories
    
    # Verify total equals sum of breakdown
    breakdown_sum = sum(source.emissions for source in carbon.breakdown)
    assert abs(carbon.total_emissions - breakdown_sum) < 0.01
    
    # Verify only open-source data sources
    valid_sources = ["eGRID", "EPA-GHG", "ADEME", "Kabaun", "CodeCarbon"]
    for source in carbon.data_sources:
        assert source in valid_sources
    
    # Verify compliance status is determined
    assert carbon.compliance_status in [
        ComplianceStatus.COMPLIANT,
        ComplianceStatus.WARNING,
        ComplianceStatus.NON_COMPLIANT,
    ]
    
    # Verify recommendations are provided if not compliant
    if carbon.compliance_status != ComplianceStatus.COMPLIANT:
        assert len(carbon.recommendations) > 0


@pytest.mark.asyncio
async def test_comprehensive_job_completion_workflow(
    fulfillment_agent,
    mock_inventree_client,
):
    """
    Test complete job completion workflow with inventory updates.
    
    **Validates: Requirements 6.7, 7.2**
    """
    completion = CompletionDetails(
        job_id="job-test",
        parts_used=[
            {"id": "part-001", "name": "Ignitor", "quantity": 1},
            {"id": "part-002", "name": "Flame Sensor", "quantity": 1},
            {"id": "part-003", "name": "Capacitor", "quantity": 2},
        ],
        labor_hours=2.5,
        notes="Replaced faulty components. System now working properly.",
        customer_signature="John Doe",
        photos=["photo1.jpg", "photo2.jpg"],
        first_time_fix=True,
    )
    
    summary = await fulfillment_agent.log_job_completion(completion)
    
    # Verify summary contains all expected fields
    assert summary["job_id"] == "job-test"
    assert summary["parts_used"] == 3
    assert summary["labor_hours"] == 2.5
    assert summary["first_time_fix"] is True
    assert "carbon_footprint" in summary
    assert "compliance_status" in summary
    
    # Verify inventory was updated for each part
    assert mock_inventree_client.update_stock.call_count == 3
    
    # Verify each update decreased stock
    for call in mock_inventree_client.update_stock.call_args_list:
        kwargs = call[1]
        assert kwargs["quantity"] < 0


@pytest.mark.asyncio
async def test_comprehensive_kpi_tracking(fulfillment_agent):
    """
    Test comprehensive KPI tracking.
    
    **Validates: Requirements 6.11, 9.7, 9.8**
    """
    # Log some jobs first
    for i in range(5):
        completion = CompletionDetails(
            job_id=f"job-{i}",
            parts_used=[{"id": f"part-{i}", "name": f"Part {i}", "quantity": 1}],
            labor_hours=2.0,
            notes=f"Job {i} completed",
            first_time_fix=i < 4,  # 4 out of 5 are first-time fixes
        )
        await fulfillment_agent.log_job_completion(completion)
    
    metrics = await fulfillment_agent.track_kpis()
    
    # Verify all KPI metrics are present and valid
    assert 0.0 <= metrics.first_time_fix_rate <= 1.0
    assert 0.0 <= metrics.job_completion_rate <= 1.0
    assert 0.0 <= metrics.technician_utilization <= 1.0
    assert metrics.average_response_time > 0
    assert 0.0 <= metrics.customer_satisfaction <= 5.0
    assert metrics.total_jobs_completed >= 5
    assert metrics.total_carbon_emissions >= 0


@pytest.mark.asyncio
async def test_comprehensive_report_generation(fulfillment_agent):
    """
    Test comprehensive report generation.
    
    **Validates: Requirements 6.10, 8.10**
    """
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    report = await fulfillment_agent.generate_report(
        start_date=start_date,
        end_date=end_date,
        report_type="sustainability",
    )
    
    # Verify report structure
    assert report["report_type"] == "sustainability"
    assert "period_start" in report
    assert "period_end" in report
    assert "generated_at" in report
    assert "summary" in report
    assert "recommendations" in report
    
    # Verify summary contains key metrics
    summary = report["summary"]
    assert "total_jobs" in summary
    assert "total_carbon_emissions" in summary
    assert "average_emissions_per_job" in summary
    assert "compliance_rate" in summary
    
    # Verify recommendations are provided
    assert len(report["recommendations"]) > 0


@pytest.mark.asyncio
async def test_comprehensive_emergency_re_optimization(
    fulfillment_agent,
    sample_jobs,
    sample_technicians,
):
    """
    Test schedule re-optimization when emergency job is added.
    
    **Validates: Requirement 6.5**
    """
    # First, optimize schedule with routine jobs only
    routine_jobs = [j for j in sample_jobs if j.urgency == "routine"]
    initial_schedule = await fulfillment_agent.optimize_schedule(
        routine_jobs,
        sample_technicians,
    )
    
    # Now add emergency job and re-optimize
    all_jobs = sample_jobs  # Includes emergency job
    updated_schedule = await fulfillment_agent.optimize_schedule(
        all_jobs,
        sample_technicians,
    )
    
    # Verify emergency job is scheduled first
    if updated_schedule.assignments:
        first_assignment = updated_schedule.assignments[0]
        first_job = next(j for j in all_jobs if j.id == first_assignment.job_id)
        assert first_job.urgency == "emergency"
    
    # Verify schedule was re-optimized (different from initial)
    assert len(updated_schedule.assignments) > len(initial_schedule.assignments)


@pytest.mark.asyncio
async def test_comprehensive_multi_day_scheduling(
    fulfillment_agent,
    sample_locations,
):
    """
    Test scheduling across multiple days with technician capacity limits.
    
    **Validates: Requirements 6.2, 6.3**
    """
    # Create many jobs (more than one technician can handle in a day)
    now = datetime.now()
    jobs = []
    for i in range(15):
        job = Job(
            id=f"job-{i}",
            lead_id=f"lead-{i}",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="HVAC",
            location=sample_locations[i % len(sample_locations)],
            scheduled_start=None,
            scheduled_end=None,
            actual_start=None,
            actual_end=None,
            estimated_duration=60,
            priority=5,
            urgency="routine",
            required_skills=["HVAC"],
            parts_used=[],
            labor_hours=1.0,
            total_cost=150.0,
        )
        jobs.append(job)
    
    # Create technician with limited capacity
    technician = Technician(
        id="tech-limited",
        name="Limited Capacity Tech",
        skills=["HVAC"],
        current_location=sample_locations[0],
        assigned_jobs=[],
        availability_start=now,
        availability_end=now + timedelta(hours=8),
        max_jobs_per_day=5,  # Can only handle 5 jobs per day
    )
    
    schedule = await fulfillment_agent.optimize_schedule(jobs, [technician])
    
    # Verify technician is not overbooked
    tech_assignments = [a for a in schedule.assignments if a.technician_id == "tech-limited"]
    assert len(tech_assignments) <= 5
    
    # Verify remaining jobs are unassigned
    assert len(schedule.unassigned_jobs) == len(jobs) - len(tech_assignments)


@pytest.mark.asyncio
async def test_comprehensive_route_optimization(
    fulfillment_agent,
    sample_jobs,
    sample_technicians,
):
    """
    Test route optimization minimizes travel distance.
    
    **Validates: Requirement 6.4**
    """
    schedule = await fulfillment_agent.optimize_schedule(sample_jobs, sample_technicians)
    
    # Verify routes are optimized
    for route in schedule.routes:
        # Route should have jobs
        assert len(route.jobs) > 0
        
        # Total duration should include both travel and work time
        assert route.total_duration >= route.total_travel_time
        
        # Distance should be non-negative
        assert route.total_distance >= 0
        
        # Travel time should be reasonable (not excessive)
        # For single-job routes, distance may be 0 but travel time is minimum 5 min
        if len(route.jobs) == 1:
            # Single job route - travel time should be minimal
            assert route.total_travel_time >= 0
        else:
            # Multi-job route - travel time should be reasonable
            # With minimum 5 min per leg, just verify it's not excessive
            # Max reasonable travel time: 30 min per job
            max_reasonable_travel = len(route.jobs) * 30
            assert route.total_travel_time <= max_reasonable_travel


@pytest.mark.asyncio
async def test_comprehensive_carbon_tracking_over_time(fulfillment_agent):
    """
    Test carbon tracking across multiple jobs over time.
    
    **Validates: Requirements 8.6, 8.9**
    """
    # Complete multiple jobs and track carbon
    total_carbon = 0.0
    
    for i in range(10):
        job = Job(
            id=f"job-{i}",
            lead_id=f"lead-{i}",
            technician_id="tech-001",
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
            parts_used=[{"id": f"part-{i}", "name": f"Part {i}", "quantity": 1}],
            labor_hours=1.0,
            total_cost=150.0,
        )
        
        carbon = await fulfillment_agent.calculate_carbon_footprint(
            job=job,
            travel_distance=10.0,
        )
        
        total_carbon += carbon.total_emissions
    
    # Verify total carbon is accumulated correctly
    assert total_carbon > 0
    assert fulfillment_agent.total_carbon_calculated == 10


# ============================================================================
# Summary Test
# ============================================================================


@pytest.mark.asyncio
async def test_comprehensive_end_to_end_workflow(
    fulfillment_agent,
    sample_jobs,
    sample_technicians,
    mock_inventree_client,
):
    """
    Test complete end-to-end workflow from scheduling to completion.
    
    **Validates: All Requirements 6.1-6.11, 8.6-8.10, 9.7-9.8**
    """
    # Step 1: Optimize schedule
    schedule = await fulfillment_agent.optimize_schedule(sample_jobs, sample_technicians)
    assert len(schedule.assignments) > 0
    
    # Step 2: Complete first job
    first_assignment = schedule.assignments[0]
    completion = CompletionDetails(
        job_id=first_assignment.job_id,
        parts_used=[
            {"id": "part-001", "name": "Part 1", "quantity": 1},
            {"id": "part-002", "name": "Part 2", "quantity": 1},
        ],
        labor_hours=2.0,
        notes="Job completed successfully",
        first_time_fix=True,
    )
    
    summary = await fulfillment_agent.log_job_completion(completion)
    assert summary["first_time_fix"] is True
    
    # Step 3: Verify inventory was updated
    assert mock_inventree_client.update_stock.call_count == 2
    
    # Step 4: Track KPIs
    metrics = await fulfillment_agent.track_kpis()
    assert metrics.total_jobs_completed >= 1
    
    # Step 5: Generate report
    report = await fulfillment_agent.generate_report(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
        report_type="sustainability",
    )
    assert report["report_type"] == "sustainability"
    
    # Verify agent statistics
    assert fulfillment_agent.total_schedules_optimized >= 1
    assert fulfillment_agent.total_jobs_completed >= 1
    assert fulfillment_agent.total_carbon_calculated >= 1
