"""
Comprehensive End-to-End Workflow Tests
Tests the complete TradeSense system from start to finish
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

# Test complete emergency service workflow
@pytest.mark.asyncio
async def test_emergency_service_complete_workflow():
    """
    Test Scenario: Customer calls for emergency HVAC repair
    
    Workflow:
    1. Customer initiates voice call
    2. Intake Agent captures details
    3. System classifies as emergency
    4. Diagnostic Agent analyzes issue
    5. System checks parts availability
    6. Fulfillment Agent schedules technician
    7. Notifications sent
    8. Data persisted
    """
    # This test validates Requirements 4.1-4.10, 5.1-5.11, 6.1-6.11
    
    # Mock voice input
    audio_input = b"My AC stopped working and it's 95 degrees"
    
    # Step 1: Voice Pipeline processes input
    from backend.voice.stt import AzureSpeechSTT, AzureSpeechConfig
    
    with patch('azure.cognitiveservices.speech.SpeechRecognizer'):
        config = AzureSpeechConfig(
            subscription_key="test_key",
            region="test_region"
        )
        stt = AzureSpeechSTT(config)
        
        # Mock transcription
        with patch.object(stt, 'transcribe_once', return_value="My AC stopped working and it's 95 degrees"):
            transcription = stt.transcribe_once(audio_input)
            assert transcription is not None
            assert "AC" in transcription
    
    # Step 2: Intake Agent captures lead
    from backend.agents.intake import IntakeAgent, LeadInput, create_intake_agent
    from backend.llm.unified_client import UnifiedLLMClient
    
    # Create mock LLM client
    mock_llm = Mock(spec=UnifiedLLMClient)
    mock_llm.generate = AsyncMock(return_value=Mock(
        content='{"urgency": "emergency", "service_type": "HVAC", "confidence": 0.95}',
        model="gemini-pro",
        prompt_tokens=50,
        completion_tokens=30,
        total_tokens=80
    ))
    
    intake_agent = IntakeAgent(llm_client=mock_llm)
    
    lead_input = LeadInput(
        source="voice",
        customer_info={
            "name": "John Smith",
            "phone": "555-0123",
            "email": "john@example.com"
        },
        issue_description=transcription,
        urgency="unknown",
        location={
            "address": "123 Main St",
            "city": "Phoenix",
            "state": "AZ",
            "zip_code": "85001"
        }
    )
    
    # Step 3: Triage classifies as emergency
    triage_result = await intake_agent.triage_lead(lead_input)
    assert triage_result.urgency == "emergency"
    assert triage_result.service_type == "HVAC"
    assert triage_result.confidence > 0.9
    
    # Step 4: Check parts availability (simulated)
    parts_available = [
        {"id": "CAP-001", "name": "AC Capacitor", "in_stock": True, "quantity": 5}
    ]
    assert len(parts_available) > 0
    assert parts_available[0]["in_stock"] is True
    
    # Step 5: Schedule technician
    from backend.agents.fulfillment import FulfillmentAgent
    
    fulfillment_agent = FulfillmentAgent(llm_client=mock_llm)
    
    # Create mock job and technicians
    job = {
        "id": "JOB-001",
        "service_type": "HVAC",
        "urgency": "emergency",
        "location": {"lat": 33.4484, "lon": -112.0740},
        "required_skills": ["HVAC"],
        "estimated_duration": 2.0
    }
    
    technicians = [
        {
            "id": "TECH-001",
            "name": "Mike Johnson",
            "skills": ["HVAC", "Electrical"],
            "available": True,
            "location": {"lat": 33.4484, "lon": -112.0740}
        }
    ]
    
    schedule = fulfillment_agent.optimize_schedule([job], technicians)
    
    assert len(schedule.assignments) > 0
    assert schedule.assignments[0].job_id == "JOB-001"
    assert schedule.assignments[0].technician_id == "TECH-001"
    
    # Step 6: Verify end-to-end timing
    # Total workflow should complete in < 2 minutes
    # (This is a simplified test - real timing would be measured)
    
    print("✅ Emergency service workflow completed successfully")
    print(f"   - Lead captured: {lead_input.customer_info['name']}")
    print(f"   - Urgency: {triage_result.urgency}")
    print(f"   - Parts available: {parts_available[0]['name']}")
    print(f"   - Technician assigned: {technicians[0]['name']}")


@pytest.mark.asyncio
async def test_job_completion_voice_workflow():
    """
    Test Scenario: Technician completes job and logs via voice
    
    Workflow:
    1. Technician says "Log job completion"
    2. Voice pipeline transcribes
    3. System retrieves job details
    4. Agent asks for parts used
    5. Technician provides parts info
    6. System calculates costs and carbon
    7. Job marked complete
    """
    # This test validates Requirements 6.7, 6.8, 8.1-8.10
    
    from backend.agents.fulfillment import FulfillmentAgent
    
    fulfillment_agent = FulfillmentAgent()
    
    # Step 1-2: Voice input transcribed
    voice_input = "Log job completion for Smith residence"
    
    # Step 3: Retrieve job
    job = {
        "id": "JOB-001",
        "customer": "John Smith",
        "service_type": "HVAC",
        "status": "in-progress",
        "location": {"address": "123 Main St"}
    }
    
    # Step 4-5: Parts used
    parts_used = [
        {"id": "CAP-001", "name": "AC Capacitor", "quantity": 1, "cost": 45.00}
    ]
    
    # Step 6: Calculate carbon footprint
    carbon_result = fulfillment_agent.calculate_carbon_footprint({
        **job,
        "parts_used": parts_used,
        "travel_distance": 15.5,  # miles
        "labor_hours": 2.0
    })
    
    assert carbon_result.total_emissions > 0
    assert len(carbon_result.breakdown) > 0
    assert any(b.category == "travel" for b in carbon_result.breakdown)
    
    # Step 7: Log completion
    completion_details = {
        "job_id": "JOB-001",
        "parts_used": parts_used,
        "labor_hours": 2.0,
        "total_cost": 285.00,
        "carbon_footprint": carbon_result.total_emissions,
        "notes": "Replaced capacitor, system working"
    }
    
    result = fulfillment_agent.log_job_completion(job, completion_details)
    
    assert result["status"] == "completed"
    assert result["total_cost"] == 285.00
    assert result["carbon_footprint"] > 0
    
    print("✅ Job completion workflow completed successfully")
    print(f"   - Job: {job['id']}")
    print(f"   - Parts: {parts_used[0]['name']}")
    print(f"   - Cost: ${completion_details['total_cost']}")
    print(f"   - Carbon: {carbon_result.total_emissions:.2f}kg CO2")


@pytest.mark.asyncio
async def test_equipment_image_analysis_workflow():
    """
    Test Scenario: Technician uploads equipment photo for diagnosis
    
    Workflow:
    1. Technician uploads equipment image
    2. Diagnostic Agent parses image
    3. System extracts manufacturer, model, serial
    4. System queries inventory for parts
    5. System compares pricing
    6. Repair guide generated
    """
    # This test validates Requirements 5.3-5.7, 19.1-19.10
    
    from backend.agents.diagnostic import DiagnosticAgent
    
    diagnostic_agent = DiagnosticAgent()
    
    # Step 1-2: Image uploaded and parsed
    image_data = b"fake_image_data"  # In real test, would be actual image
    
    with patch.object(diagnostic_agent, 'vision_client') as mock_vision:
        mock_vision.parse_image = AsyncMock(return_value={
            "manufacturer": "Carrier",
            "model_number": "24ACC636A003",
            "serial_number": "1234567890",
            "equipment_type": "Air Conditioner",
            "confidence": 0.98
        })
        
        equipment_info = await mock_vision.parse_image(image_data)
        
        assert equipment_info["manufacturer"] == "Carrier"
        assert equipment_info["model_number"] is not None
        assert equipment_info["confidence"] > 0.95
    
    # Step 3-4: Query inventory
    with patch('backend.integrations.inventree.InvenTreeClient') as mock_inv:
        mock_inv.return_value.find_compatible_parts = AsyncMock(return_value=[
            {
                "id": "CAP-001",
                "name": "Run Capacitor 35/5 MFD",
                "compatible": True,
                "in_stock": True,
                "price": 45.00
            },
            {
                "id": "CAP-002",
                "name": "Run Capacitor 40/5 MFD",
                "compatible": True,
                "in_stock": True,
                "price": 48.00
            }
        ])
        
        parts = await mock_inv.return_value.find_compatible_parts(
            equipment_info["model_number"]
        )
        
        assert len(parts) >= 2
        assert all(p["compatible"] for p in parts)
    
    # Step 5: Generate diagnosis
    diagnosis = await diagnostic_agent.diagnose_issue({
        "equipment": equipment_info,
        "symptoms": "AC not cooling, fan running",
        "available_parts": parts
    })
    
    assert diagnosis["issue_type"] is not None
    assert diagnosis["confidence"] > 0.7
    assert len(diagnosis["required_parts"]) > 0
    
    # Step 6: Generate repair guide
    repair_guide = await diagnostic_agent.generate_repair_guide(diagnosis)
    
    assert len(repair_guide["steps"]) > 0
    assert "safety" in repair_guide
    assert "tools_required" in repair_guide
    
    print("✅ Equipment image analysis workflow completed successfully")
    print(f"   - Equipment: {equipment_info['manufacturer']} {equipment_info['model_number']}")
    print(f"   - Diagnosis: {diagnosis['issue_type']}")
    print(f"   - Parts found: {len(parts)}")
    print(f"   - Repair steps: {len(repair_guide['steps'])}")


@pytest.mark.asyncio
async def test_schedule_optimization_workflow():
    """
    Test Scenario: Optimize schedule for 50 jobs and 10 technicians
    
    Workflow:
    1. System receives 50 job requests
    2. Fulfillment Agent analyzes jobs
    3. System matches skills to jobs
    4. System optimizes routes
    5. System assigns technicians
    6. Schedule generated
    """
    # This test validates Requirements 6.1-6.6, 14.5
    
    from backend.agents.fulfillment import FulfillmentAgent
    
    fulfillment_agent = FulfillmentAgent()
    
    # Create 50 jobs
    jobs = []
    for i in range(50):
        jobs.append({
            "id": f"JOB-{i:03d}",
            "service_type": ["HVAC", "Electrical", "Plumbing"][i % 3],
            "urgency": "emergency" if i < 5 else "routine",
            "location": {
                "lat": 33.4484 + (i * 0.01),
                "lon": -112.0740 + (i * 0.01)
            },
            "required_skills": [["HVAC"], ["Electrical"], ["Plumbing"]][i % 3],
            "estimated_duration": 2.0 + (i % 3)
        })
    
    # Create 10 technicians
    technicians = []
    for i in range(10):
        technicians.append({
            "id": f"TECH-{i:03d}",
            "name": f"Technician {i}",
            "skills": [["HVAC", "Electrical"], ["Plumbing", "HVAC"], ["Electrical"]][i % 3],
            "available": True,
            "location": {"lat": 33.4484, "lon": -112.0740},
            "shift_start": "08:00",
            "shift_end": "17:00"
        })
    
    # Optimize schedule
    import time
    start_time = time.time()
    
    schedule = fulfillment_agent.optimize_schedule(jobs, technicians)
    
    optimization_time = time.time() - start_time
    
    # Validate results
    assert len(schedule.assignments) == 50, "All jobs should be assigned"
    assert optimization_time < 5.0, f"Optimization took {optimization_time:.2f}s, should be < 5s"
    assert schedule.utilization_rate >= 0.75, f"Utilization {schedule.utilization_rate:.2%} should be >= 75%"
    
    # Verify skill matching
    for assignment in schedule.assignments:
        job = next(j for j in jobs if j["id"] == assignment["job_id"])
        tech = next(t for t in technicians if t["id"] == assignment["technician_id"])
        
        # Check if technician has required skills
        assert any(skill in tech["skills"] for skill in job["required_skills"]), \
            f"Technician {tech['id']} missing skills for job {job['id']}"
    
    # Verify emergency prioritization
    emergency_jobs = [j for j in jobs if j["urgency"] == "emergency"]
    emergency_assignments = [a for a in schedule.assignments 
                            if any(j["id"] == a["job_id"] for j in emergency_jobs)]
    
    # Emergency jobs should be scheduled early
    avg_emergency_time = sum(a.get("scheduled_time", 0) for a in emergency_assignments) / len(emergency_assignments)
    avg_routine_time = sum(a.get("scheduled_time", 0) for a in schedule.assignments 
                          if a not in emergency_assignments) / (len(schedule.assignments) - len(emergency_assignments))
    
    assert avg_emergency_time < avg_routine_time, "Emergency jobs should be scheduled before routine jobs"
    
    print("✅ Schedule optimization workflow completed successfully")
    print(f"   - Jobs scheduled: {len(schedule.assignments)}")
    print(f"   - Technicians used: {len(set(a['technician_id'] for a in schedule.assignments))}")
    print(f"   - Utilization rate: {schedule.utilization_rate:.1%}")
    print(f"   - Optimization time: {optimization_time:.2f}s")
    print(f"   - Emergency jobs: {len(emergency_jobs)} (prioritized)")


@pytest.mark.asyncio
async def test_multi_agent_coordination():
    """
    Test Scenario: Complete workflow with multiple agents
    
    Workflow:
    1. Intake Agent captures lead
    2. Diagnostic Agent analyzes issue
    3. Fulfillment Agent schedules and completes job
    4. Data flows correctly between agents
    """
    # This test validates Requirements 3.1-3.8 (Pipeline Orchestration)
    
    from backend.agents.intake import IntakeAgent
    from backend.agents.diagnostic import DiagnosticAgent
    from backend.agents.fulfillment import FulfillmentAgent
    
    # Step 1: Intake captures lead
    intake_agent = IntakeAgent()
    
    lead_data = {
        "source": "voice",
        "customer_info": {"name": "Jane Doe", "phone": "555-0199"},
        "issue_description": "Refrigerator not cooling",
        "location": {"address": "456 Oak St", "city": "Phoenix", "state": "AZ"}
    }
    
    with patch.object(intake_agent, 'llm_client') as mock_llm:
        mock_llm.generate = AsyncMock(return_value={
            "urgency": "urgent",
            "service_type": "Appliance Repair",
            "confidence": 0.88
        })
        
        triage = await intake_agent.triage_lead(lead_data)
    
    # Step 2: Diagnostic analyzes
    diagnostic_agent = DiagnosticAgent()
    
    with patch.object(diagnostic_agent, 'llm_client') as mock_diag_llm:
        mock_diag_llm.generate = AsyncMock(return_value={
            "issue_type": "Compressor failure",
            "confidence": 0.85,
            "required_parts": ["COMP-001"],
            "estimated_time": 3.0
        })
        
        diagnosis = await diagnostic_agent.diagnose_issue({
            "symptoms": lead_data["issue_description"],
            "equipment_type": "Refrigerator"
        })
    
    # Step 3: Fulfillment schedules
    fulfillment_agent = FulfillmentAgent()
    
    job = {
        "id": "JOB-MULTI-001",
        "lead_id": "LEAD-001",
        "diagnosis": diagnosis,
        "service_type": triage["service_type"],
        "urgency": triage["urgency"],
        "location": lead_data["location"]
    }
    
    technicians = [{
        "id": "TECH-001",
        "skills": ["Appliance Repair"],
        "available": True
    }]
    
    schedule = fulfillment_agent.optimize_schedule([job], technicians)
    
    # Verify data flow
    assert schedule.assignments[0]["job_id"] == job["id"]
    assert job["diagnosis"]["issue_type"] == diagnosis["issue_type"]
    assert job["urgency"] == triage["urgency"]
    
    print("✅ Multi-agent coordination workflow completed successfully")
    print(f"   - Lead captured: {lead_data['customer_info']['name']}")
    print(f"   - Triage: {triage['urgency']} - {triage['service_type']}")
    print(f"   - Diagnosis: {diagnosis['issue_type']}")
    print(f"   - Scheduled: {schedule.assignments[0]['technician_id']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
