"""
Example usage of Fulfillment Agent.

Demonstrates:
- Schedule optimization with multiple jobs and technicians
- Emergency job prioritization
- Carbon footprint calculation
- Job completion logging
- KPI tracking
- Report generation

Run with: python -m examples.test_fulfillment_agent
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.fulfillment import (
    FulfillmentAgent,
    Job,
    Technician,
    GeoLocation,
    JobStatus,
    CompletionDetails,
    create_fulfillment_agent,
)
from llm.unified_client import UnifiedLLMClient, LLMProvider


async def main():
    """Run Fulfillment Agent examples."""
    print("=" * 80)
    print("Fulfillment Agent Example")
    print("=" * 80)
    print()
    
    # Initialize LLM client
    print("Initializing LLM client...")
    llm_client = UnifiedLLMClient(
        primary_provider=LLMProvider.GEMINI,
        fallback_provider=LLMProvider.AZURE_OPENAI,
    )
    
    # Create fulfillment agent
    print("Creating Fulfillment Agent...")
    agent = create_fulfillment_agent(llm_client=llm_client)
    print()
    
    # ========================================================================
    # Example 1: Schedule Optimization
    # ========================================================================
    
    print("=" * 80)
    print("Example 1: Schedule Optimization")
    print("=" * 80)
    print()
    
    # Create sample locations
    location1 = GeoLocation(
        latitude=40.7128,
        longitude=-74.0060,
        address="123 Main St",
        city="New York",
        state="NY",
        zip_code="10001",
    )
    
    location2 = GeoLocation(
        latitude=40.7589,
        longitude=-73.9851,
        address="456 Broadway",
        city="New York",
        state="NY",
        zip_code="10036",
    )
    
    location3 = GeoLocation(
        latitude=40.7614,
        longitude=-73.9776,
        address="789 Park Ave",
        city="New York",
        state="NY",
        zip_code="10065",
    )
    
    # Create sample jobs
    jobs = [
        Job(
            id="job-001",
            lead_id="lead-001",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="HVAC",
            location=location1,
            scheduled_start=None,
            scheduled_end=None,
            actual_start=None,
            actual_end=None,
            estimated_duration=120,
            priority=10,  # Emergency
            urgency="emergency",
            required_skills=["HVAC"],
            parts_used=[],
            labor_hours=2.0,
            total_cost=350.0,
            notes="Furnace not working, no heat",
        ),
        Job(
            id="job-002",
            lead_id="lead-002",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="Plumbing",
            location=location2,
            scheduled_start=None,
            scheduled_end=None,
            actual_start=None,
            actual_end=None,
            estimated_duration=90,
            priority=6,  # Urgent
            urgency="urgent",
            required_skills=["Plumbing"],
            parts_used=[],
            labor_hours=1.5,
            total_cost=220.0,
            notes="Leaking faucet",
        ),
        Job(
            id="job-003",
            lead_id="lead-003",
            technician_id=None,
            status=JobStatus.SCHEDULED,
            service_type="HVAC",
            location=location3,
            scheduled_start=None,
            scheduled_end=None,
            actual_start=None,
            actual_end=None,
            estimated_duration=60,
            priority=3,  # Routine
            urgency="routine",
            required_skills=["HVAC"],
            parts_used=[],
            labor_hours=1.0,
            total_cost=150.0,
            notes="AC tune-up",
        ),
    ]
    
    # Create sample technicians
    now = datetime.now()
    technicians = [
        Technician(
            id="tech-001",
            name="John Smith",
            skills=["HVAC", "Electrical"],
            current_location=location1,
            assigned_jobs=[],
            availability_start=now,
            availability_end=now + timedelta(hours=8),
            max_jobs_per_day=8,
        ),
        Technician(
            id="tech-002",
            name="Jane Doe",
            skills=["Plumbing", "HVAC"],
            current_location=location2,
            assigned_jobs=[],
            availability_start=now,
            availability_end=now + timedelta(hours=8),
            max_jobs_per_day=8,
        ),
    ]
    
    print(f"Jobs to schedule: {len(jobs)}")
    print(f"Available technicians: {len(technicians)}")
    print()
    
    for job in jobs:
        print(f"  - {job.id}: {job.service_type} ({job.urgency}) - {job.notes}")
    print()
    
    for tech in technicians:
        print(f"  - {tech.id}: {tech.name} - Skills: {', '.join(tech.skills)}")
    print()
    
    # Optimize schedule
    print("Optimizing schedule...")
    schedule = await agent.optimize_schedule(jobs, technicians)
    
    print(f"\nSchedule optimized:")
    print(f"  - Assignments: {len(schedule.assignments)}")
    print(f"  - Routes: {len(schedule.routes)}")
    print(f"  - Utilization rate: {schedule.utilization_rate:.1%}")
    print(f"  - Estimated completion time: {schedule.estimated_completion_time} minutes")
    
    if schedule.unassigned_jobs:
        print(f"  - Unassigned jobs: {len(schedule.unassigned_jobs)}")
    
    print("\nAssignments:")
    for assignment in schedule.assignments:
        job = next(j for j in jobs if j.id == assignment.job_id)
        tech = next(t for t in technicians if t.id == assignment.technician_id)
        print(f"  - {job.id} ({job.urgency}) → {tech.name}")
        print(f"    Scheduled: {assignment.scheduled_start.strftime('%H:%M')} - {assignment.scheduled_end.strftime('%H:%M')}")
        print(f"    Travel time: {assignment.travel_time} min, Duration: {assignment.estimated_duration} min")
    
    print("\nRoutes:")
    for route in schedule.routes:
        tech = next(t for t in technicians if t.id == route.technician_id)
        print(f"  - {tech.name}:")
        print(f"    Jobs: {len(route.jobs)}")
        print(f"    Total distance: {route.total_distance:.1f} miles")
        print(f"    Total travel time: {route.total_travel_time} min")
        print(f"    Total duration: {route.total_duration} min")
    
    print()
    
    # ========================================================================
    # Example 2: Carbon Footprint Calculation
    # ========================================================================
    
    print("=" * 80)
    print("Example 2: Carbon Footprint Calculation")
    print("=" * 80)
    print()
    
    # Create completed job with parts
    completed_job = Job(
        id="job-completed",
        lead_id="lead-completed",
        technician_id="tech-001",
        status=JobStatus.COMPLETED,
        service_type="HVAC",
        location=location1,
        scheduled_start=now,
        scheduled_end=now + timedelta(hours=2),
        actual_start=now,
        actual_end=now + timedelta(hours=2),
        estimated_duration=120,
        priority=5,
        urgency="routine",
        required_skills=["HVAC"],
        parts_used=[
            {"id": "part-001", "name": "Thermostat", "quantity": 1},
            {"id": "part-002", "name": "Capacitor", "quantity": 1},
        ],
        labor_hours=2.0,
        total_cost=285.0,
    )
    
    print(f"Calculating carbon footprint for job: {completed_job.id}")
    print(f"  - Service type: {completed_job.service_type}")
    print(f"  - Parts used: {len(completed_job.parts_used)}")
    print(f"  - Labor hours: {completed_job.labor_hours}")
    print(f"  - Travel distance: 15.5 miles")
    print()
    
    carbon = await agent.calculate_carbon_footprint(
        job=completed_job,
        travel_distance=15.5,
    )
    
    print(f"Carbon footprint calculated:")
    print(f"  - Total emissions: {carbon.total_emissions:.2f} kg CO2")
    print(f"  - Compliance status: {carbon.compliance_status.value}")
    print()
    
    print("Breakdown by category:")
    for source in carbon.breakdown:
        print(f"  - {source.category.value}: {source.emissions:.2f} kg CO2 (source: {source.data_source})")
    
    print()
    print("Data sources used:")
    for source in carbon.data_sources:
        print(f"  - {source}")
    
    if carbon.recommendations:
        print()
        print("Recommendations:")
        for rec in carbon.recommendations:
            print(f"  - {rec}")
    
    print()
    
    # ========================================================================
    # Example 3: Job Completion Logging
    # ========================================================================
    
    print("=" * 80)
    print("Example 3: Job Completion Logging")
    print("=" * 80)
    print()
    
    completion = CompletionDetails(
        job_id="job-001",
        parts_used=[
            {"id": "part-001", "name": "Ignitor", "quantity": 1},
            {"id": "part-002", "name": "Flame Sensor", "quantity": 1},
        ],
        labor_hours=2.5,
        notes="Replaced faulty ignitor and flame sensor. Furnace now working properly.",
        first_time_fix=True,
    )
    
    print(f"Logging job completion: {completion.job_id}")
    print(f"  - Parts used: {len(completion.parts_used)}")
    print(f"  - Labor hours: {completion.labor_hours}")
    print(f"  - First-time fix: {completion.first_time_fix}")
    print(f"  - Notes: {completion.notes}")
    print()
    
    summary = await agent.log_job_completion(completion)
    
    print("Job completion logged:")
    print(f"  - Job ID: {summary['job_id']}")
    print(f"  - Parts used: {summary['parts_used']}")
    print(f"  - Labor hours: {summary['labor_hours']}")
    print(f"  - First-time fix: {summary['first_time_fix']}")
    print(f"  - Carbon footprint: {summary['carbon_footprint']:.2f} kg CO2")
    print(f"  - Compliance status: {summary['compliance_status']}")
    print()
    
    # ========================================================================
    # Example 4: KPI Tracking
    # ========================================================================
    
    print("=" * 80)
    print("Example 4: KPI Tracking")
    print("=" * 80)
    print()
    
    print("Tracking KPIs...")
    metrics = await agent.track_kpis()
    
    print("\nKey Performance Indicators:")
    print(f"  - First-time fix rate: {metrics.first_time_fix_rate:.1%}")
    print(f"  - Job completion rate: {metrics.job_completion_rate:.1%}")
    print(f"  - Technician utilization: {metrics.technician_utilization:.1%}")
    print(f"  - Average response time: {metrics.average_response_time} minutes")
    print(f"  - Customer satisfaction: {metrics.customer_satisfaction:.1f}/5.0")
    print(f"  - Total jobs completed: {metrics.total_jobs_completed}")
    print(f"  - Total carbon emissions: {metrics.total_carbon_emissions:.2f} kg CO2")
    print()
    
    # ========================================================================
    # Example 5: Report Generation
    # ========================================================================
    
    print("=" * 80)
    print("Example 5: Report Generation")
    print("=" * 80)
    print()
    
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    print(f"Generating sustainability report...")
    print(f"  - Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print()
    
    report = await agent.generate_report(
        start_date=start_date,
        end_date=end_date,
        report_type="sustainability",
    )
    
    print("Sustainability Report:")
    print(f"  - Report type: {report['report_type']}")
    print(f"  - Period: {report['period_start']} to {report['period_end']}")
    print(f"  - Generated at: {report['generated_at']}")
    print()
    
    print("Summary:")
    for key, value in report['summary'].items():
        print(f"  - {key}: {value}")
    
    print()
    print("Recommendations:")
    for rec in report['recommendations']:
        print(f"  - {rec}")
    
    print()
    
    # ========================================================================
    # Summary
    # ========================================================================
    
    print("=" * 80)
    print("Summary")
    print("=" * 80)
    print()
    
    print("Fulfillment Agent Statistics:")
    print(f"  - Total schedules optimized: {agent.total_schedules_optimized}")
    print(f"  - Total jobs completed: {agent.total_jobs_completed}")
    print(f"  - Total carbon calculations: {agent.total_carbon_calculated}")
    print()
    
    print("✓ All examples completed successfully!")
    print()


if __name__ == "__main__":
    asyncio.run(main())
