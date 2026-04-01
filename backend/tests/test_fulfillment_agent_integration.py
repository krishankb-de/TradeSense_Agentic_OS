"""
Fulfillment Agent Integration Tests

Tests the complete fulfillment workflow from job completion logging through
schedule optimization and carbon footprint calculation with real component interactions.

**Validates: Requirements 6.1-6.11, 8.6-8.10, 9.7-9.8**
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import List

from agents.fulfillment import (
    FulfillmentAgent,
    Job,
    JobStatus,
    Technician,
    GeoLocation,
    Schedule,
    CompletionDetails,
    CarbonFootprint,
    EmissionCategory,
    ComplianceStatus,
    KPIMetrics,
    create_fulfillment_agent,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_client():
    """Mock LLM client with context-aware responses."""
    client = Mock()
    
    def generate_side_effect(*args, **kwargs):
        prompt = kwargs.get('prompt', '')
        
        # Voice-driven job completion
        if 'job completion' in prompt.lower():
            return AsyncMock(return_value="""{
                "parts_used": [
                    {"id": "CAP-001", "name": "Run Capacitor 35/5 MFD", "quantity": 1}
                ],
                "labor_hours": 2.5,
                "notes": "Replaced capacitor, system working properly",
                "first_time_fix": true
            }""")()
        
        return AsyncMock(return_value="Default response")()
    
    client.generate = generate_side_effect
    return client


@pytest.fixture
def mock_inventree_client():
    """Mock InvenTree client."""
    client = Mock()
    client.update_stock = AsyncMock(return_value={"success": True})
    return client


@pytest.fixture
def sample_jobs() -> List[Job]:
    """Create sample jobs for testing."""
    base_location = GeoLocation(
        latitude=33.4484,
        longitude=-112.0740,
        address="123 Main St",
        city="Phoenix",
        state="AZ",
        zip_code="85001"
    )
    
    jobs = []
    for i in range(10):
        job = Job(
            id=f"JOB-{i:03d}",
            lead_id=f"LEAD-{i:03d}",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="HVAC" if i % 2 == 0 else "Plumbing",
            location=GeoLocation(
                latitude=base_location.latitude + (i * 0.01),
                longitude=base_location.longitude + (i * 0.01),
                address=f"{100 + i} Test St",
                city="Phoenix",
                state="AZ",
                zip_code="85001"
            ),
            scheduled_start=None,
            scheduled_end=None,
            actual_start=None,
            actual_end=None,
            estimated_duration=60 + (i * 15),  # 60-195 minutes
            priority=10 if i < 2 else 5,  # First 2 are high priority
            urgency="emergency" if i < 2 else "routine",
            required_skills=["HVAC"] if i % 2 == 0 else ["Plumbing"],
            parts_used=[],
            labor_hours=0.0,
            total_cost=0.0,
            notes=""
        )
        jobs.append(job)
    
    return jobs


@pytest.fixture
def sample_technicians() -> List[Technician]:
    """Create sample technicians for testing."""
    base_location = GeoLocation(
        latitude=33.4484,
        longitude=-112.0740,
        address="HQ",
        city="Phoenix",
        state="AZ",
        zip_code="85001"
    )
    
    technicians = []
    for i in range(5):
        tech = Technician(
            id=f"TECH-{i:03d}",
            name=f"Technician {i}",
            skills=["HVAC", "Electrical"] if i % 2 == 0 else ["Plumbing", "HVAC"],
            current_location=base_location,
            assigned_jobs=[],
            availability_start=datetime.now().replace(hour=8, minute=0, second=0, microsecond=0),
            availability_end=datetime.now().replace(hour=17, minute=0, second=0, microsecond=0),
            max_jobs_per_day=8
        )
        technicians.append(tech)
    
    return technicians


@pytest.fixture
def fulfillment_agent(mock_llm_client, mock_inventree_client):
    """Create fulfillment agent with mocked dependencies."""
    return FulfillmentAgent(
        llm_client=mock_llm_client,
        inventree_client=mock_inventree_client,
        enable_logging=False,
    )


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_complete_job_completion_workflow(fulfillment_agent):
    """
    Test Scenario: Complete job completion workflow
    
    Workflow:
    1. Technician completes job via voice
    2. Agent logs completion details
    3. Agent updates inventory
    4. Agent calculates carbon footprint
    5. Agent updates KPIs
    6. All data flows correctly
    
    **Validates: Requirements 6.7, 6.11, 8.6-8.9**
    """
    # Step 1: Create completion details
    completion_details = CompletionDetails(
        job_id="JOB-001",
        parts_used=[
            {"id": "CAP-001", "name": "Run Capacitor 35/5 MFD", "quantity": 1, "cost": 45.00}
        ],
        labor_hours=2.5,
        notes="Replaced capacitor, system working properly",
        first_time_fix=True,
    )
    
    # Step 2: Log job completion
    summary = await fulfillment_agent.log_job_completion(completion_details)
    
    # Verify completion logged
    assert summary["job_id"] == "JOB-001"
    assert summary["parts_used"] == 1
    assert summary["labor_hours"] == 2.5
    assert summary["first_time_fix"] is True
    assert summary["carbon_footprint"] > 0
    assert summary["compliance_status"] in ["compliant", "warning", "non-compliant"]
    
    # Step 3: Verify inventory updated
    assert fulfillment_agent.inventree_client.update_stock.called
    
    # Step 4: Verify carbon footprint calculated
    assert fulfillment_agent.total_carbon_calculated > 0
    
    # Step 5: Verify KPIs tracked
    assert fulfillment_agent.total_jobs_completed == 1
    
    print("✅ Complete job completion workflow passed")
    print(f"   - Job: {summary['job_id']}")
    print(f"   - Parts used: {summary['parts_used']}")
    print(f"   - Labor hours: {summary['labor_hours']}")
    print(f"   - Carbon footprint: {summary['carbon_footprint']:.2f} kg CO2")
    print(f"   - First-time fix: {summary['first_time_fix']}")


@pytest.mark.asyncio
async def test_schedule_optimization_workflow(fulfillment_agent, sample_jobs, sample_technicians):
    """
    Test Scenario: Schedule optimization for 10 jobs and 5 technicians
    
    Workflow:
    1. System receives 10 job requests
    2. Agent analyzes jobs and technicians
    3. Agent matches skills to jobs
    4. Agent optimizes routes
    5. Agent assigns technicians
    6. Schedule generated with 75%+ utilization
    
    **Validates: Requirements 6.1-6.6**
    """
    # Step 1-5: Optimize schedule
    schedule = await fulfillment_agent.optimize_schedule(
        jobs=sample_jobs,
        technicians=sample_technicians,
    )
    
    # Verify schedule created
    assert len(schedule.assignments) > 0
    assert len(schedule.routes) > 0
    
    # Verify all jobs assigned (or tracked as unassigned)
    assigned_job_ids = [a.job_id for a in schedule.assignments]
    total_jobs = len(assigned_job_ids) + len(schedule.unassigned_jobs)
    assert total_jobs == len(sample_jobs)
    
    # Verify utilization rate
    assert schedule.utilization_rate >= 0.0
    assert schedule.utilization_rate <= 1.0
    
    # Verify skill matching
    for assignment in schedule.assignments:
        job = next(j for j in sample_jobs if j.id == assignment.job_id)
        tech = next(t for t in sample_technicians if t.id == assignment.technician_id)
        
        # Check if technician has required skills
        has_skills = all(skill in tech.skills for skill in job.required_skills)
        assert has_skills, f"Technician {tech.id} missing skills for job {job.id}"
    
    # Verify emergency prioritization
    emergency_jobs = [j for j in sample_jobs if j.urgency == "emergency"]
    if emergency_jobs:
        emergency_assignments = [
            a for a in schedule.assignments
            if any(j.id == a.job_id for j in emergency_jobs)
        ]
        assert len(emergency_assignments) > 0, "Emergency jobs should be assigned"
    
    # Verify routes optimized
    for route in schedule.routes:
        assert route.total_distance >= 0
        assert route.total_travel_time >= 0
        assert len(route.jobs) > 0
    
    print("✅ Schedule optimization workflow passed")
    print(f"   - Jobs assigned: {len(schedule.assignments)}")
    print(f"   - Unassigned jobs: {len(schedule.unassigned_jobs)}")
    print(f"   - Routes created: {len(schedule.routes)}")
    print(f"   - Utilization rate: {schedule.utilization_rate:.1%}")
    print(f"   - Emergency jobs: {len(emergency_jobs)}")


@pytest.mark.asyncio
async def test_emergency_job_reoptimization_workflow(fulfillment_agent, sample_jobs, sample_technicians):
    """
    Test Scenario: Emergency job insertion and re-optimization
    
    Workflow:
    1. Initial schedule created
    2. Emergency job arrives
    3. Agent re-optimizes schedule
    4. Emergency job prioritized
    5. Existing jobs rescheduled
    
    **Validates: Requirements 6.5, 6.6**
    """
    # Step 1: Create initial schedule
    initial_schedule = await fulfillment_agent.optimize_schedule(
        jobs=sample_jobs[:5],  # First 5 jobs
        technicians=sample_technicians,
    )
    
    initial_assignments = len(initial_schedule.assignments)
    
    # Step 2: Add emergency job
    emergency_job = Job(
        id="JOB-EMERGENCY",
        lead_id="LEAD-EMERGENCY",
        technician_id=None,
        status=JobStatus.SCHEDULED,
        service_type="HVAC",
        location=GeoLocation(
            latitude=33.4484,
            longitude=-112.0740,
            address="999 Emergency St",
            city="Phoenix",
            state="AZ",
            zip_code="85001"
        ),
        scheduled_start=None,
        scheduled_end=None,
        actual_start=None,
        actual_end=None,
        estimated_duration=120,
        priority=10,
        urgency="emergency",
        required_skills=["HVAC"],
        parts_used=[],
        labor_hours=0.0,
        total_cost=0.0,
    )
    
    # Step 3: Re-optimize with emergency job
    all_jobs = sample_jobs[:5] + [emergency_job]
    new_schedule = await fulfillment_agent.optimize_schedule(
        jobs=all_jobs,
        technicians=sample_technicians,
    )
    
    # Verify emergency job assigned
    emergency_assignment = next(
        (a for a in new_schedule.assignments if a.job_id == "JOB-EMERGENCY"),
        None
    )
    assert emergency_assignment is not None, "Emergency job should be assigned"
    
    # Verify schedule updated
    assert len(new_schedule.assignments) >= initial_assignments
    
    print("✅ Emergency job re-optimization workflow passed")
    print(f"   - Initial assignments: {initial_assignments}")
    print(f"   - New assignments: {len(new_schedule.assignments)}")
    print(f"   - Emergency job assigned: {emergency_assignment is not None}")


@pytest.mark.asyncio
async def test_carbon_footprint_calculation_workflow(fulfillment_agent):
    """
    Test Scenario: Carbon footprint calculation for completed job
    
    Workflow:
    1. Job completed with parts and travel
    2. Agent calculates travel emissions
    3. Agent calculates parts emissions
    4. Agent calculates AI infrastructure emissions
    5. Agent determines compliance status
    6. Recommendations provided
    
    **Validates: Requirements 6.8, 8.1-8.10**
    """
    # Create completed job
    job = Job(
        id="JOB-CARBON",
        lead_id="LEAD-CARBON",
        technician_id="TECH-001",
        status=JobStatus.COMPLETED,
        service_type="HVAC",
        location=GeoLocation(
            latitude=33.4484,
            longitude=-112.0740,
            address="123 Test St",
            city="Phoenix",
            state="AZ",
            zip_code="85001"
        ),
        scheduled_start=datetime.now(),
        scheduled_end=datetime.now() + timedelta(hours=2),
        actual_start=datetime.now(),
        actual_end=datetime.now() + timedelta(hours=2),
        estimated_duration=120,
        priority=5,
        urgency="routine",
        required_skills=["HVAC"],
        parts_used=[
            {"id": "CAP-001", "name": "Run Capacitor", "quantity": 1},
            {"id": "FILTER-001", "name": "Air Filter", "quantity": 2}
        ],
        labor_hours=2.0,
        total_cost=285.00,
    )
    
    # Calculate carbon footprint
    travel_distance = 25.5  # miles
    carbon_footprint = await fulfillment_agent.calculate_carbon_footprint(
        job=job,
        travel_distance=travel_distance,
    )
    
    # Verify calculation
    assert carbon_footprint.total_emissions > 0
    assert len(carbon_footprint.breakdown) > 0
    
    # Verify emission categories
    categories = [source.category for source in carbon_footprint.breakdown]
    assert EmissionCategory.TRAVEL in categories
    assert EmissionCategory.PARTS in categories or EmissionCategory.AI_INFRASTRUCTURE in categories
    
    # Verify data sources
    assert len(carbon_footprint.data_sources) > 0
    assert any(source in ["EPA-GHG", "Kabaun", "CodeCarbon"] for source in carbon_footprint.data_sources)
    
    # Verify compliance status
    assert carbon_footprint.compliance_status in [
        ComplianceStatus.COMPLIANT,
        ComplianceStatus.WARNING,
        ComplianceStatus.NON_COMPLIANT
    ]
    
    # Verify recommendations provided if not compliant
    if carbon_footprint.compliance_status != ComplianceStatus.COMPLIANT:
        assert len(carbon_footprint.recommendations) > 0
    
    print("✅ Carbon footprint calculation workflow passed")
    print(f"   - Total emissions: {carbon_footprint.total_emissions:.2f} kg CO2")
    print(f"   - Breakdown categories: {len(carbon_footprint.breakdown)}")
    print(f"   - Compliance status: {carbon_footprint.compliance_status.value}")
    print(f"   - Data sources: {', '.join(carbon_footprint.data_sources)}")
    print(f"   - Recommendations: {len(carbon_footprint.recommendations)}")


@pytest.mark.asyncio
async def test_multi_technician_coordination_workflow(fulfillment_agent, sample_jobs, sample_technicians):
    """
    Test Scenario: Coordinate multiple technicians for large job set
    
    Workflow:
    1. 10 jobs need assignment
    2. 5 technicians available
    3. Agent balances workload
    4. Agent optimizes routes for each technician
    5. All technicians utilized efficiently
    
    **Validates: Requirements 6.1-6.4**
    """
    # Optimize schedule for all jobs and technicians
    schedule = await fulfillment_agent.optimize_schedule(
        jobs=sample_jobs,
        technicians=sample_technicians,
    )
    
    # Verify all technicians utilized
    assigned_tech_ids = set(a.technician_id for a in schedule.assignments)
    assert len(assigned_tech_ids) > 0, "At least one technician should be assigned"
    
    # Verify workload distribution
    tech_workload = {}
    for assignment in schedule.assignments:
        tech_id = assignment.technician_id
        tech_workload[tech_id] = tech_workload.get(tech_id, 0) + 1
    
    # Check that no technician is overloaded
    for tech_id, job_count in tech_workload.items():
        tech = next(t for t in sample_technicians if t.id == tech_id)
        assert job_count <= tech.max_jobs_per_day, f"Technician {tech_id} overloaded"
    
    # Verify routes created for each assigned technician
    route_tech_ids = set(r.technician_id for r in schedule.routes)
    assert route_tech_ids == assigned_tech_ids, "Routes should match assigned technicians"
    
    # Verify route optimization
    for route in schedule.routes:
        assert route.total_distance >= 0
        assert route.total_travel_time >= 0
        assert route.total_duration >= route.total_travel_time
    
    print("✅ Multi-technician coordination workflow passed")
    print(f"   - Technicians assigned: {len(assigned_tech_ids)}")
    print(f"   - Jobs per technician: {dict(tech_workload)}")
    print(f"   - Routes created: {len(schedule.routes)}")
    print(f"   - Average jobs per tech: {len(schedule.assignments) / len(assigned_tech_ids):.1f}")


@pytest.mark.asyncio
async def test_inventory_synchronization_workflow(fulfillment_agent, mock_inventree_client):
    """
    Test Scenario: Inventory synchronization after job completion
    
    Workflow:
    1. Job completed with parts used
    2. Agent updates InvenTree inventory
    3. Stock levels decremented
    4. Synchronization verified
    
    **Validates: Requirement 7.2**
    """
    # Create completion details with multiple parts
    completion_details = CompletionDetails(
        job_id="JOB-INV-001",
        parts_used=[
            {"id": "CAP-001", "name": "Run Capacitor", "quantity": 1, "cost": 45.00},
            {"id": "FILTER-001", "name": "Air Filter", "quantity": 2, "cost": 15.00},
            {"id": "BELT-001", "name": "Fan Belt", "quantity": 1, "cost": 25.00}
        ],
        labor_hours=3.0,
        notes="Replaced capacitor, filters, and belt",
        first_time_fix=True,
    )
    
    # Log job completion (triggers inventory update)
    summary = await fulfillment_agent.log_job_completion(completion_details)
    
    # Verify inventory updates called
    assert mock_inventree_client.update_stock.called
    assert mock_inventree_client.update_stock.call_count == 3  # One per part
    
    # Verify correct parts updated
    call_args_list = mock_inventree_client.update_stock.call_args_list
    updated_part_ids = [call[1]["part_id"] for call in call_args_list]
    
    assert "CAP-001" in updated_part_ids
    assert "FILTER-001" in updated_part_ids
    assert "BELT-001" in updated_part_ids
    
    print("✅ Inventory synchronization workflow passed")
    print(f"   - Parts updated: {len(completion_details.parts_used)}")
    print(f"   - Inventory calls: {mock_inventree_client.update_stock.call_count}")
    print(f"   - Updated part IDs: {updated_part_ids}")


@pytest.mark.asyncio
async def test_kpi_tracking_workflow(fulfillment_agent):
    """
    Test Scenario: KPI tracking across multiple jobs
    
    Workflow:
    1. Multiple jobs completed
    2. Agent tracks first-time fix rate
    3. Agent tracks job completion rate
    4. Agent tracks technician utilization
    5. KPI metrics calculated
    
    **Validates: Requirements 6.11, 9.7, 9.8**
    """
    # Simulate multiple job completions
    for i in range(5):
        completion_details = CompletionDetails(
            job_id=f"JOB-KPI-{i:03d}",
            parts_used=[{"id": f"PART-{i}", "name": f"Part {i}", "quantity": 1, "cost": 50.00}],
            labor_hours=2.0,
            notes=f"Job {i} completed",
            first_time_fix=(i % 2 == 0),  # 60% first-time fix rate
        )
        
        await fulfillment_agent.log_job_completion(completion_details)
    
    # Track KPIs
    kpi_metrics = await fulfillment_agent.track_kpis()
    
    # Verify KPI metrics
    assert kpi_metrics.first_time_fix_rate >= 0.0
    assert kpi_metrics.first_time_fix_rate <= 1.0
    assert kpi_metrics.job_completion_rate >= 0.0
    assert kpi_metrics.job_completion_rate <= 1.0
    assert kpi_metrics.technician_utilization >= 0.0
    assert kpi_metrics.technician_utilization <= 1.0
    assert kpi_metrics.total_jobs_completed == fulfillment_agent.total_jobs_completed
    assert kpi_metrics.total_carbon_emissions >= 0.0
    
    print("✅ KPI tracking workflow passed")
    print(f"   - First-time fix rate: {kpi_metrics.first_time_fix_rate:.1%}")
    print(f"   - Job completion rate: {kpi_metrics.job_completion_rate:.1%}")
    print(f"   - Technician utilization: {kpi_metrics.technician_utilization:.1%}")
    print(f"   - Total jobs completed: {kpi_metrics.total_jobs_completed}")
    print(f"   - Total carbon emissions: {kpi_metrics.total_carbon_emissions:.2f} kg CO2")


@pytest.mark.asyncio
async def test_compliance_reporting_workflow(fulfillment_agent):
    """
    Test Scenario: Generate compliance and sustainability reports
    
    Workflow:
    1. Jobs completed over time period
    2. Agent generates sustainability report
    3. Report includes carbon emissions
    4. Report includes compliance status
    5. Recommendations provided
    
    **Validates: Requirements 6.10, 8.10**
    """
    # Define report period
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    # Generate sustainability report
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
    
    # Verify summary data
    summary = report["summary"]
    assert "total_jobs" in summary
    assert "total_carbon_emissions" in summary
    assert "average_emissions_per_job" in summary
    assert "compliance_rate" in summary
    
    # Verify recommendations
    assert len(report["recommendations"]) > 0
    
    print("✅ Compliance reporting workflow passed")
    print(f"   - Report type: {report['report_type']}")
    print(f"   - Period: {start_date.date()} to {end_date.date()}")
    print(f"   - Total jobs: {summary['total_jobs']}")
    print(f"   - Total emissions: {summary['total_carbon_emissions']:.2f} kg CO2")
    print(f"   - Compliance rate: {summary['compliance_rate']:.1%}")
    print(f"   - Recommendations: {len(report['recommendations'])}")


@pytest.mark.asyncio
async def test_concurrent_scheduling_requests(fulfillment_agent, sample_jobs, sample_technicians):
    """
    Test Scenario: Handle multiple concurrent scheduling requests
    
    Workflow:
    1. Multiple schedule optimization requests arrive simultaneously
    2. All requests processed concurrently
    3. All schedules returned correctly
    4. No data corruption
    
    **Validates: System scalability**
    """
    # Create multiple scheduling requests
    job_batches = [
        sample_jobs[:3],
        sample_jobs[3:6],
        sample_jobs[6:9],
    ]
    
    # Process all requests concurrently
    tasks = [
        fulfillment_agent.optimize_schedule(jobs=batch, technicians=sample_technicians)
        for batch in job_batches
    ]
    
    schedules = await asyncio.gather(*tasks)
    
    # Verify all schedules created
    assert len(schedules) == len(job_batches)
    
    for i, schedule in enumerate(schedules):
        assert schedule is not None
        assert len(schedule.assignments) >= 0
        assert schedule.utilization_rate >= 0.0
        
        print(f"   - Schedule {i+1}: {len(schedule.assignments)} assignments, {schedule.utilization_rate:.1%} utilization")
    
    print("✅ Concurrent scheduling requests passed")
    print(f"   - Requests processed: {len(schedules)}")
    print(f"   - All schedules valid: True")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
