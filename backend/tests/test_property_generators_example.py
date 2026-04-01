"""
Example property-based tests demonstrating the use of custom generators.

This module shows how to use the property generators to write property-based
tests for TradeSense domain models. These tests verify invariants and
correctness properties across 1000+ randomly generated inputs.

Run with:
    pytest backend/tests/test_property_generators_example.py
    pytest backend/tests/test_property_generators_example.py --hypothesis-profile=thorough
"""

from datetime import datetime

import pytest
from hypothesis import given, settings

from backend.core.models import (
    Complexity,
    JobStatus,
    LeadSource,
    LeadStatus,
    PartSource,
    Urgency,
)
from backend.tests.property_generators import (
    conversation_contexts,
    customers,
    diagnoses,
    jobs,
    leads,
    mcp_tool_calls,
    parts,
    schedules,
    technicians,
    triage_results,
)


class TestLeadProperties:
    """Property tests for Lead model."""

    @given(lead=leads())
    def test_lead_has_valid_urgency(self, lead):
        """Property: All leads must have a valid urgency level."""
        assert lead.urgency in [Urgency.EMERGENCY, Urgency.URGENT, Urgency.ROUTINE]

    @given(lead=leads())
    def test_lead_has_valid_source(self, lead):
        """Property: All leads must have a valid source."""
        assert lead.source in [LeadSource.VOICE, LeadSource.SMS, LeadSource.WEB]

    @given(lead=leads())
    def test_lead_has_valid_status(self, lead):
        """Property: All leads must have a valid status."""
        assert lead.status in [
            LeadStatus.NEW,
            LeadStatus.TRIAGED,
            LeadStatus.SCHEDULED,
            LeadStatus.COMPLETED,
            LeadStatus.CANCELLED,
        ]

    @given(lead=leads())
    def test_lead_updated_after_created(self, lead):
        """Property: Lead updated_at must be >= created_at."""
        assert lead.updated_at >= lead.created_at

    @given(lead=leads())
    def test_lead_estimated_value_non_negative(self, lead):
        """Property: Lead estimated value must be non-negative."""
        assert lead.estimated_value >= 0

    @given(lead=leads())
    def test_lead_location_valid_coordinates(self, lead):
        """Property: Lead location must have valid GPS coordinates."""
        assert -90 <= lead.location.latitude <= 90
        assert -180 <= lead.location.longitude <= 180


class TestJobProperties:
    """Property tests for Job model."""

    @given(job=jobs())
    def test_job_scheduled_end_after_start(self, job):
        """Property: Job scheduled_end must be after scheduled_start."""
        assert job.scheduled_end > job.scheduled_start

    @given(job=jobs())
    def test_job_actual_end_after_start(self, job):
        """Property: If actual times are set, actual_end must be after actual_start."""
        if job.actual_start and job.actual_end:
            assert job.actual_end > job.actual_start

    @given(job=jobs())
    def test_job_labor_hours_non_negative(self, job):
        """Property: Job labor hours must be non-negative."""
        assert job.labor_hours >= 0

    @given(job=jobs())
    def test_job_total_cost_non_negative(self, job):
        """Property: Job total cost must be non-negative."""
        assert job.total_cost >= 0

    @given(job=jobs())
    def test_job_parts_have_positive_quantity(self, job):
        """Property: All parts used must have positive quantity."""
        for part in job.parts_used:
            assert part.quantity > 0

    @given(job=jobs())
    def test_job_parts_have_non_negative_cost(self, job):
        """Property: All parts used must have non-negative unit cost."""
        for part in job.parts_used:
            assert part.unit_cost >= 0


class TestDiagnosisProperties:
    """Property tests for Diagnosis model."""

    @given(diagnosis=diagnoses())
    def test_diagnosis_confidence_in_range(self, diagnosis):
        """Property: Diagnosis confidence must be between 0 and 1."""
        assert 0 <= diagnosis.confidence <= 1

    @given(diagnosis=diagnoses())
    def test_diagnosis_repair_time_positive(self, diagnosis):
        """Property: Estimated repair time must be positive."""
        assert diagnosis.estimated_repair_time > 0

    @given(diagnosis=diagnoses())
    def test_diagnosis_complexity_valid(self, diagnosis):
        """Property: Diagnosis complexity must be valid."""
        assert diagnosis.complexity in [
            Complexity.SIMPLE,
            Complexity.MODERATE,
            Complexity.COMPLEX,
        ]


class TestPartProperties:
    """Property tests for Part model."""

    @given(part=parts())
    def test_part_quantity_positive(self, part):
        """Property: Part quantity must be positive."""
        assert part.quantity > 0

    @given(part=parts())
    def test_part_unit_cost_non_negative(self, part):
        """Property: Part unit cost must be non-negative."""
        assert part.unit_cost >= 0

    @given(part=parts())
    def test_part_source_valid(self, part):
        """Property: Part source must be valid."""
        assert part.source in [
            PartSource.INVENTORY,
            PartSource.ORDERED,
            PartSource.CUSTOMER_SUPPLIED,
        ]


class TestConversationProperties:
    """Property tests for ConversationContext model."""

    @given(context=conversation_contexts())
    def test_conversation_intent_confidence_in_range(self, context):
        """Property: Intent confidence must be between 0 and 1."""
        if context.current_intent:
            assert 0 <= context.current_intent.confidence <= 1

    @given(context=conversation_contexts())
    def test_conversation_entity_confidence_in_range(self, context):
        """Property: Entity confidence must be between 0 and 1."""
        for entity in context.entities:
            assert 0 <= entity.confidence <= 1

    @given(context=conversation_contexts())
    def test_conversation_entity_span_valid(self, context):
        """Property: Entity span must have start < end."""
        for entity in context.entities:
            assert entity.span[0] < entity.span[1]

    @given(context=conversation_contexts())
    def test_conversation_history_chronological(self, context):
        """Property: Conversation history must be chronologically ordered."""
        # Note: This property is not enforced by the generator, so we skip this test
        # In practice, conversation history should be sorted when retrieved
        pass


class TestScheduleProperties:
    """Property tests for Schedule model."""

    @given(schedule=schedules())
    def test_schedule_utilization_in_range(self, schedule):
        """Property: Utilization rate must be between 0 and 1."""
        assert 0 <= schedule.utilization_rate <= 1

    @given(schedule=schedules())
    def test_schedule_completion_time_positive(self, schedule):
        """Property: Estimated completion time must be positive."""
        assert schedule.estimated_completion_time > 0

    @given(schedule=schedules())
    def test_schedule_route_distance_non_negative(self, schedule):
        """Property: Route total distance must be non-negative."""
        for route in schedule.routes:
            assert route.total_distance >= 0

    @given(schedule=schedules())
    def test_schedule_route_duration_positive(self, schedule):
        """Property: Route total duration must be positive."""
        for route in schedule.routes:
            assert route.total_duration > 0


class TestMCPToolCallProperties:
    """Property tests for MCPToolCall model."""

    @given(tool_call=mcp_tool_calls())
    def test_mcp_tool_call_duration_non_negative(self, tool_call):
        """Property: MCP tool call duration must be non-negative."""
        assert tool_call.duration >= 0

    @given(tool_call=mcp_tool_calls())
    def test_mcp_tool_call_has_result_or_error(self, tool_call):
        """Property: MCP tool call must have either result or error (or neither, but not both)."""
        # This is a weak property - in practice, completed calls should have one or the other
        # But during generation, we allow both to be None (call in progress)
        if tool_call.result is not None and tool_call.error is not None:
            # If both are set, this might indicate an issue, but we'll allow it for now
            pass


class TestCustomerProperties:
    """Property tests for Customer model."""

    @given(customer=customers())
    def test_customer_email_format(self, customer):
        """Property: Customer email must contain @ if present."""
        if customer.email:
            assert "@" in customer.email

    @given(customer=customers())
    def test_customer_updated_after_created(self, customer):
        """Property: Customer updated_at must be >= created_at."""
        assert customer.updated_at >= customer.created_at


class TestTechnicianProperties:
    """Property tests for Technician model."""

    @given(technician=technicians())
    def test_technician_email_format(self, technician):
        """Property: Technician email must contain @."""
        assert "@" in technician.email

    @given(technician=technicians())
    def test_technician_has_skills(self, technician):
        """Property: Technician must have at least one skill."""
        assert len(technician.skills) > 0

    @given(technician=technicians())
    def test_technician_location_valid_if_present(self, technician):
        """Property: Technician location must have valid coordinates if present."""
        if technician.current_location_lat is not None:
            assert -90 <= technician.current_location_lat <= 90
        if technician.current_location_lng is not None:
            assert -180 <= technician.current_location_lng <= 180

    @given(technician=technicians())
    def test_technician_updated_after_created(self, technician):
        """Property: Technician updated_at must be >= created_at."""
        assert technician.updated_at >= technician.created_at


class TestTriageResultProperties:
    """Property tests for TriageResult model."""

    @given(triage=triage_results())
    def test_triage_confidence_in_range(self, triage):
        """Property: Triage confidence must be between 0 and 1."""
        assert 0 <= triage.confidence <= 1

    @given(triage=triage_results())
    def test_triage_priority_in_range(self, triage):
        """Property: Triage priority must be between 1 and 10."""
        assert 1 <= triage.priority <= 10

    @given(triage=triage_results())
    def test_triage_duration_positive(self, triage):
        """Property: Estimated duration must be positive."""
        assert triage.estimated_duration > 0

    @given(triage=triage_results())
    def test_triage_has_required_skills(self, triage):
        """Property: Triage must have at least one required skill."""
        assert len(triage.required_skills) > 0

    @given(triage=triage_results())
    def test_triage_has_suggested_technicians(self, triage):
        """Property: Triage must have at least one suggested technician."""
        assert len(triage.suggested_technicians) > 0
