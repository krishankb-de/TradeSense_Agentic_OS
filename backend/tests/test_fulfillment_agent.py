"""
Unit tests for Fulfillment Agent.

Tests:
- Schedule optimization with skill matching
- Route optimization
- Emergency job prioritization
- Carbon footprint calculation
- Compliance reporting
- KPI tracking
- Inventory synchronization

**Validates: Requirements 6.1-6.11, 8.6-8.10, 9.7-9.8**
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

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
def fulfillment_agent(mock_llm_client):
    """Create fulfillment agent for testing."""
    return FulfillmentAgent(
        llm_client=mock_llm_client,
        enable_logging=False,
    )


@pytest.fixture
def sample_location():
    """Sample geographic location."""
    return GeoLocation(
        latitude=40.7128,
        longitude=-74.0060,
        address="123 Main St",
        city="New York",
        state="NY",
        zip_code="10001",
    )


@pytest.fixture
def sample_technician(sample_location):
    """Sample technician."""
    return Technician(
        id="tech-001",
        name="John Doe",
        skills=["HVAC", "Plumbing", "Electrical"],
        current_location=sample_location,
        assigned_jobs=[],
        availability_start=datetime.now(),
        availability_end=datetime.now() + timedelta(hours=8),
        max_jobs_per_day=8,
    )


@pytest.fixture
def sample_job(sample_location):
    """Sample job."""
    return Job(
        id="job-001",
        lead_id="lead-001",
        technician_id=None,
        status=JobStatus.SCHEDULED,
        service_type="HVAC",
        location=sample_location,
        scheduled_start=None,
        scheduled_end=None,
        actual_start=None,
        actual_end=None,
        estimated_duration=120,
        priority=5,
        urgency="routine",
        required_skills=["HVAC"],
        parts_used=[],
        labor_hours=2.0,
        total_cost=250.0,
    )


# ============================================================================
# Test Schedule Optimization
# ============================================================================


@pytest.mark.asyncio
async def test_optimize_schedule_basic(fulfillment_agent, sample_job, sample_technician):
    """Test basic schedule optimization."""
    jobs = [sample_job]
    technicians = [sample_technician]
    
    schedule = await fulfillment_agent.optimize_schedule(jobs, technicians)
    
    assert len(schedule.assignments) == 1
    assert schedule.assignments[0].job_id == sample_job.id
    assert schedule.assignments[0].technician_id == sample_technician.id
    assert schedule.utilization_rate > 0


@pytest.mark.asyncio
async def test_optimize_schedule_skill_matching(fulfillment_agent, sample_location):
    """Test that technicians are matched based on required skills."""
    # Create jobs with different skill requirements
    hvac_job = Job(
        id="job-hvac",
        lead_id="lead-001",
        technician_id=None,
        status=JobStatus.SCHEDULED,
        service_type="HVAC",
        location=sample_location,
        scheduled_start=None,
        scheduled_end=None,
        actual_start=None,
        actual_end=None,
        estimated_duration=120,
        priority=5,
        urgency="routine",
        required_skills=["HVAC"],
        parts_used=[],
        labor_hours=2.0,
        total_cost=250.0,
    )
    
    plumbing_job = Job(
        id="job-plumbing",
        lead_id="lead-002",
        technician_id=None,
        status=JobStatus.SCHEDULED,
        service_type="Plumbing",
        location=sample_location,
        scheduled_start=None,
        scheduled_end=None,
        actual_start=None,
        actual_end=None,
        estimated_duration=90,
        priority=5,
        urgency="routine",
        required_skills=["Plumbing"],
        parts_used=[],
        labor_hours=1.5,
        total_cost=180.0,
    )
    
    # Create technicians with different skills
    hvac_tech = Technician(
        id="tech-hvac",
        name="HVAC Specialist",
        skills=["HVAC"],
        current_location=sample_location,
        assigned_jobs=[],
        availability_start=datetime.now(),
        availability_end=datetime.now() + timedelta(hours=8),
    )
    
    plumbing_tech = Technician(
        id="tech-plumbing",
        name="Plumbing Specialist",
        skills=["Plumbing"],
        current_location=sample_location,
        assigned_jobs=[],
        availability_start=datetime.now(),
        availability_end=datetime.now() + timedelta(hours=8),
    )
    
    jobs = [hvac_job, plumbing_job]
    technicians = [hvac_tech, plumbing_tech]
    
    schedule = await fulfillment_agent.optimize_schedule(jobs, technicians)
    
    # Verify skill matching
    assert len(schedule.assignments) == 2
    
    hvac_assignment = next(a for a in schedule.assignments if a.job_id == "job-hvac")
    assert hvac_assignment.technician_id == "tech-hvac"
    
    plumbing_assignment = next(a for a in schedule.assignments if a.job_id == "job-plumbing")
    assert plumbing_assignment.technician_id == "tech-plumbing"


@pytest.mark.asyncio
async def test_optimize_schedule_emergency_priority(fulfillment_agent, sample_location):
    """Test that emergency jobs are prioritized over routine jobs."""
    # Create emergency and routine jobs
    emergency_job = Job(
        id="job-emergency",
        lead_id="lead-001",
        technician_id=None,
        status=JobStatus.SCHEDULED,
        service_type="HVAC",
        location=sample_location,
        scheduled_start=None,
        scheduled_end=None,
        actual_start=None,
        actual_end=None,
        estimated_duration=120,
        priority=10,  # High priority
        urgency="emergency",
        required_skills=["HVAC"],
        parts_used=[],
        labor_hours=2.0,
        total_cost=350.0,
    )
    
    routine_job = Job(
        id="job-routine",
        lead_id="lead-002",
        technician_id=None,
        status=JobStatus.SCHEDULED,
        service_type="HVAC",
        location=sample_location,
        scheduled_start=None,
        scheduled_end=None,
        actual_start=None,
        actual_end=None,
        estimated_duration=90,
        priority=3,  # Low priority
        urgency="routine",
        required_skills=["HVAC"],
        parts_used=[],
        labor_hours=1.5,
        total_cost=180.0,
    )
    
    technician = Technician(
        id="tech-001",
        name="Technician",
        skills=["HVAC"],
        current_location=sample_location,
        assigned_jobs=[],
        availability_start=datetime.now(),
        availability_end=datetime.now() + timedelta(hours=8),
    )
    
    # Submit jobs in reverse priority order
    jobs = [routine_job, emergency_job]
    technicians = [technician]
    
    schedule = await fulfillment_agent.optimize_schedule(jobs, technicians)
    
    # Verify emergency job is scheduled first
    assert len(schedule.assignments) == 2
    assert schedule.assignments[0].job_id == "job-emergency"
    assert schedule.assignments[1].job_id == "job-routine"


@pytest.mark.asyncio
async def test_optimize_schedule_utilization_rate(fulfillment_agent, sample_location):
    """Test that utilization rate is calculated correctly."""
    # Create multiple jobs
    jobs = []
    for i in range(5):
        job = Job(
            id=f"job-{i}",
            lead_id=f"lead-{i}",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="HVAC",
            location=sample_location,
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
    
    technician = Technician(
        id="tech-001",
        name="Technician",
        skills=["HVAC"],
        current_location=sample_location,
        assigned_jobs=[],
        availability_start=datetime.now(),
        availability_end=datetime.now() + timedelta(hours=8),
    )
    
    technicians = [technician]
    
    schedule = await fulfillment_agent.optimize_schedule(jobs, technicians)
    
    # Verify utilization rate
    # 5 jobs * 60 min = 300 min work time
    # 8 hours = 480 min available time
    # Utilization = 300 / 480 = 0.625
    assert schedule.utilization_rate > 0.6
    assert schedule.utilization_rate < 0.7


@pytest.mark.asyncio
async def test_optimize_schedule_no_eligible_technician(fulfillment_agent, sample_location):
    """Test handling when no technician has required skills."""
    job = Job(
        id="job-001",
        lead_id="lead-001",
        technician_id=None,
        status=JobStatus.SCHEDULED,
        service_type="Specialized",
        location=sample_location,
        scheduled_start=None,
        scheduled_end=None,
        actual_start=None,
        actual_end=None,
        estimated_duration=120,
        priority=5,
        urgency="routine",
        required_skills=["Specialized Skill"],
        parts_used=[],
        labor_hours=2.0,
        total_cost=250.0,
    )
    
    technician = Technician(
        id="tech-001",
        name="Technician",
        skills=["HVAC"],  # Doesn't have required skill
        current_location=sample_location,
        assigned_jobs=[],
        availability_start=datetime.now(),
        availability_end=datetime.now() + timedelta(hours=8),
    )
    
    jobs = [job]
    technicians = [technician]
    
    schedule = await fulfillment_agent.optimize_schedule(jobs, technicians)
    
    # Verify job is unassigned
    assert len(schedule.assignments) == 0
    assert "job-001" in schedule.unassigned_jobs


# ============================================================================
# Test Carbon Footprint Calculation
# ============================================================================


@pytest.mark.asyncio
async def test_calculate_carbon_footprint_basic(fulfillment_agent, sample_job):
    """Test basic carbon footprint calculation."""
    carbon = await fulfillment_agent.calculate_carbon_footprint(
        job=sample_job,
        travel_distance=10.0,
    )
    
    assert carbon.total_emissions > 0
    assert len(carbon.breakdown) > 0
    assert carbon.compliance_status in [
        ComplianceStatus.COMPLIANT,
        ComplianceStatus.WARNING,
        ComplianceStatus.NON_COMPLIANT,
    ]


@pytest.mark.asyncio
async def test_calculate_carbon_footprint_categories(fulfillment_agent, sample_job):
    """Test that all emission categories are included."""
    # Add parts to job
    sample_job.parts_used = [
        {"id": "part-001", "name": "Part 1", "quantity": 2},
        {"id": "part-002", "name": "Part 2", "quantity": 1},
    ]
    
    carbon = await fulfillment_agent.calculate_carbon_footprint(
        job=sample_job,
        travel_distance=15.0,
    )
    
    # Verify all categories are present
    categories = [source.category for source in carbon.breakdown]
    assert EmissionCategory.TRAVEL in categories
    assert EmissionCategory.PARTS in categories
    assert EmissionCategory.AI_INFRASTRUCTURE in categories


@pytest.mark.asyncio
async def test_calculate_carbon_footprint_data_sources(fulfillment_agent, sample_job):
    """Test that open-source data sources are used."""
    carbon = await fulfillment_agent.calculate_carbon_footprint(
        job=sample_job,
        travel_distance=10.0,
    )
    
    # Verify open-source data sources
    valid_sources = ["eGRID", "EPA-GHG", "ADEME", "Kabaun", "CodeCarbon"]
    for source in carbon.data_sources:
        assert source in valid_sources


@pytest.mark.asyncio
async def test_calculate_carbon_footprint_compliance_status(fulfillment_agent, sample_job):
    """Test compliance status determination."""
    # Low emissions job
    sample_job.parts_used = []
    carbon_low = await fulfillment_agent.calculate_carbon_footprint(
        job=sample_job,
        travel_distance=5.0,
    )
    assert carbon_low.compliance_status == ComplianceStatus.COMPLIANT
    
    # High emissions job
    sample_job.parts_used = [{"id": f"part-{i}", "name": f"Part {i}", "quantity": 1} for i in range(10)]
    carbon_high = await fulfillment_agent.calculate_carbon_footprint(
        job=sample_job,
        travel_distance=50.0,
    )
    assert carbon_high.compliance_status in [ComplianceStatus.WARNING, ComplianceStatus.NON_COMPLIANT]


# ============================================================================
# Test Job Completion Logging
# ============================================================================


@pytest.mark.asyncio
async def test_log_job_completion_basic(fulfillment_agent):
    """Test basic job completion logging."""
    completion = CompletionDetails(
        job_id="job-001",
        parts_used=[{"id": "part-001", "name": "Part 1", "quantity": 1}],
        labor_hours=2.0,
        notes="Job completed successfully",
        first_time_fix=True,
    )
    
    summary = await fulfillment_agent.log_job_completion(completion)
    
    assert summary["job_id"] == "job-001"
    assert summary["parts_used"] == 1
    assert summary["labor_hours"] == 2.0
    assert summary["first_time_fix"] is True
    assert "carbon_footprint" in summary


@pytest.mark.asyncio
async def test_log_job_completion_with_inventory_update(mock_llm_client, mock_inventree_client):
    """Test job completion with inventory update."""
    agent = FulfillmentAgent(
        llm_client=mock_llm_client,
        inventree_client=mock_inventree_client,
        enable_logging=False,
    )
    
    completion = CompletionDetails(
        job_id="job-001",
        parts_used=[
            {"id": "part-001", "name": "Part 1", "quantity": 2},
            {"id": "part-002", "name": "Part 2", "quantity": 1},
        ],
        labor_hours=2.0,
        notes="Job completed",
        first_time_fix=True,
    )
    
    await agent.log_job_completion(completion)
    
    # Verify inventory was updated
    assert mock_inventree_client.update_stock.call_count == 2


# ============================================================================
# Test KPI Tracking
# ============================================================================


@pytest.mark.asyncio
async def test_track_kpis(fulfillment_agent):
    """Test KPI tracking."""
    metrics = await fulfillment_agent.track_kpis()
    
    assert 0.0 <= metrics.first_time_fix_rate <= 1.0
    assert 0.0 <= metrics.job_completion_rate <= 1.0
    assert 0.0 <= metrics.technician_utilization <= 1.0
    assert metrics.average_response_time > 0
    assert 0.0 <= metrics.customer_satisfaction <= 5.0
    assert metrics.total_jobs_completed >= 0
    assert metrics.total_carbon_emissions >= 0


# ============================================================================
# Test Report Generation
# ============================================================================


@pytest.mark.asyncio
async def test_generate_report_sustainability(fulfillment_agent):
    """Test sustainability report generation."""
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    report = await fulfillment_agent.generate_report(
        start_date=start_date,
        end_date=end_date,
        report_type="sustainability",
    )
    
    assert report["report_type"] == "sustainability"
    assert "period_start" in report
    assert "period_end" in report
    assert "summary" in report
    assert "recommendations" in report


# ============================================================================
# Test Helper Methods
# ============================================================================


def test_has_required_skills(fulfillment_agent, sample_technician):
    """Test skill matching logic."""
    assert fulfillment_agent._has_required_skills(sample_technician, ["HVAC"])
    assert fulfillment_agent._has_required_skills(sample_technician, ["HVAC", "Plumbing"])
    assert not fulfillment_agent._has_required_skills(sample_technician, ["Specialized"])


def test_calculate_travel_time(fulfillment_agent):
    """Test travel time calculation."""
    loc1 = GeoLocation(40.7128, -74.0060, "", "", "", "")  # NYC
    loc2 = GeoLocation(40.7589, -73.9851, "", "", "", "")  # Times Square
    
    travel_time = fulfillment_agent._calculate_travel_time(loc1, loc2)
    
    assert travel_time >= 5  # Minimum 5 minutes
    assert travel_time < 60  # Should be less than 1 hour for nearby locations


def test_calculate_distance(fulfillment_agent):
    """Test distance calculation."""
    loc1 = GeoLocation(40.7128, -74.0060, "", "", "", "")  # NYC
    loc2 = GeoLocation(40.7589, -73.9851, "", "", "", "")  # Times Square
    
    distance = fulfillment_agent._calculate_distance(loc1, loc2)
    
    assert distance > 0
    assert distance < 10  # Should be less than 10 miles


# ============================================================================
# Test Factory Function
# ============================================================================


def test_create_fulfillment_agent(mock_llm_client):
    """Test factory function."""
    agent = create_fulfillment_agent(llm_client=mock_llm_client)
    
    assert isinstance(agent, FulfillmentAgent)
    assert agent.llm_client == mock_llm_client
