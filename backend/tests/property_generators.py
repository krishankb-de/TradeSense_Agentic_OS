"""
Property-based test generators for TradeSense domain models.

This module provides Hypothesis strategies for generating valid instances
of all domain models used in the TradeSense system. These generators are
used by property-based tests to verify correctness properties across
1000+ randomly generated inputs.

Usage:
    from tests.property_generators import leads, jobs, customers
    
    @given(lead=leads())
    def test_lead_property(lead):
        assert lead.urgency in [Urgency.EMERGENCY, Urgency.URGENT, Urgency.ROUTINE]
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4

from hypothesis import strategies as st

from backend.core.models import (
    Availability,
    CarbonFootprint,
    Complexity,
    ComplianceStatus,
    ConversationContext,
    ConversationTurn,
    Customer,
    Diagnosis,
    Entity,
    EquipmentInfo,
    GeoLocation,
    Intent,
    Job,
    JobAssignment,
    JobStatus,
    Lead,
    LeadSource,
    LeadStatus,
    MCPError,
    MCPToolCall,
    Part,
    PartSource,
    PartsRecommendation,
    Route,
    Schedule,
    Technician,
    TechnicianStatus,
    TriageResult,
    Urgency,
    UserRole,
)


# ============================================================================
# Primitive Strategies
# ============================================================================


@st.composite
def uuids(draw) -> str:
    """Generate valid UUID strings."""
    return str(uuid4())


@st.composite
def datetimes_recent(draw, min_days_ago: int = 30, max_days_ago: int = 0) -> datetime:
    """Generate recent datetime values."""
    now = datetime.now()
    days_ago = draw(st.integers(min_value=max_days_ago, max_value=min_days_ago))
    return now - timedelta(days=days_ago)


@st.composite
def datetimes_future(draw, min_days_ahead: int = 0, max_days_ahead: int = 30) -> datetime:
    """Generate future datetime values."""
    now = datetime.now()
    days_ahead = draw(st.integers(min_value=min_days_ahead, max_value=max_days_ahead))
    return now + timedelta(days=days_ahead)


@st.composite
def emails(draw) -> str:
    """Generate valid email addresses."""
    username = draw(st.text(alphabet=st.characters(whitelist_categories=("Ll", "Nd")), min_size=3, max_size=20))
    domain = draw(st.text(alphabet=st.characters(whitelist_categories=("Ll",)), min_size=3, max_size=15))
    tld = draw(st.sampled_from(["com", "org", "net", "io", "dev"]))
    return f"{username}@{domain}.{tld}"


@st.composite
def phone_numbers(draw) -> str:
    """Generate valid phone numbers."""
    area_code = draw(st.integers(min_value=200, max_value=999))
    exchange = draw(st.integers(min_value=200, max_value=999))
    number = draw(st.integers(min_value=1000, max_value=9999))
    return f"+1-{area_code}-{exchange}-{number}"


# ============================================================================
# Base Model Strategies
# ============================================================================


@st.composite
def geo_locations(draw) -> GeoLocation:
    """Generate valid GeoLocation instances."""
    return GeoLocation(
        latitude=draw(st.floats(min_value=-90, max_value=90)),
        longitude=draw(st.floats(min_value=-180, max_value=180)),
        address=draw(st.text(min_size=10, max_size=100)),
        city=draw(st.text(min_size=3, max_size=50)),
        state=draw(st.sampled_from(["CA", "NY", "TX", "FL", "IL", "PA", "OH"])),
        zipCode=draw(st.text(alphabet=st.characters(whitelist_categories=("Nd",)), min_size=5, max_size=5)),
    )


@st.composite
def parts(draw) -> Part:
    """Generate valid Part instances."""
    return Part(
        id=draw(uuids()),
        name=draw(st.text(min_size=5, max_size=50)),
        manufacturer=draw(st.sampled_from(["Honeywell", "Carrier", "Trane", "Lennox", "Rheem"])),
        modelNumber=draw(st.text(alphabet=st.characters(whitelist_categories=("Lu", "Nd")), min_size=5, max_size=20)),
        quantity=draw(st.integers(min_value=1, max_value=100)),
        unitCost=draw(st.floats(min_value=1.0, max_value=1000.0)),
        source=draw(st.sampled_from(list(PartSource))),
    )


# ============================================================================
# Lead Model Strategies
# ============================================================================


@st.composite
def leads(draw) -> Lead:
    """Generate valid Lead instances."""
    created = draw(datetimes_recent(min_days_ago=30, max_days_ago=0))
    updated = created + timedelta(hours=draw(st.integers(min_value=0, max_value=48)))
    
    return Lead(
        id=draw(uuids()),
        customerId=draw(uuids()),
        source=draw(st.sampled_from(list(LeadSource))),
        status=draw(st.sampled_from(list(LeadStatus))),
        issueDescription=draw(st.text(min_size=20, max_size=500)),
        urgency=draw(st.sampled_from(list(Urgency))),
        serviceType=draw(st.sampled_from(["HVAC", "Plumbing", "Electrical", "Appliance Repair"])),
        location=draw(geo_locations()),
        createdAt=created,
        updatedAt=updated,
        assignedTechnicianId=draw(st.one_of(st.none(), uuids())),
        estimatedValue=draw(st.floats(min_value=50.0, max_value=5000.0)),
    )


@st.composite
def triage_results(draw) -> TriageResult:
    """Generate valid TriageResult instances."""
    return TriageResult(
        serviceType=draw(st.sampled_from(["HVAC", "Plumbing", "Electrical", "Appliance Repair"])),
        estimatedDuration=draw(st.integers(min_value=30, max_value=480)),
        requiredSkills=draw(st.lists(st.sampled_from(["HVAC", "Electrical", "Plumbing", "Diagnostics"]), min_size=1, max_size=3)),
        suggestedTechnicians=draw(st.lists(uuids(), min_size=1, max_size=5)),
        priority=draw(st.integers(min_value=1, max_value=10)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
    )


# ============================================================================
# Job Model Strategies
# ============================================================================


@st.composite
def diagnoses(draw) -> Diagnosis:
    """Generate valid Diagnosis instances."""
    return Diagnosis(
        issueType=draw(st.sampled_from(["Compressor Failure", "Refrigerant Leak", "Thermostat Malfunction", "Electrical Issue"])),
        rootCause=draw(st.text(min_size=20, max_size=200)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        requiredParts=draw(st.lists(parts(), min_size=0, max_size=5)),
        estimatedRepairTime=draw(st.integers(min_value=30, max_value=480)),
        complexity=draw(st.sampled_from(list(Complexity))),
        reasoningSteps=draw(st.lists(st.text(min_size=10, max_size=100), min_size=0, max_size=5)),
    )


@st.composite
def carbon_footprints(draw) -> CarbonFootprint:
    """Generate valid CarbonFootprint instances."""
    return CarbonFootprint(
        totalEmissions=draw(st.floats(min_value=0.0, max_value=100.0)),
        breakdown=[
            {"category": "travel", "emissions": draw(st.floats(min_value=0.0, max_value=50.0))},
            {"category": "parts", "emissions": draw(st.floats(min_value=0.0, max_value=30.0))},
        ],
        complianceStatus=draw(st.sampled_from(list(ComplianceStatus))),
        recommendations=draw(st.lists(st.text(min_size=10, max_size=100), min_size=0, max_size=3)),
        dataSources=draw(st.lists(st.sampled_from(["eGRID", "EPA-GHG", "ADEME", "Kabaun"]), min_size=1, max_size=4)),
    )


@st.composite
def jobs(draw) -> Job:
    """Generate valid Job instances."""
    scheduled_start = draw(datetimes_future(min_days_ahead=0, max_days_ahead=30))
    scheduled_end = scheduled_start + timedelta(hours=draw(st.integers(min_value=1, max_value=8)))
    
    # Actual times may or may not be set
    has_actual_times = draw(st.booleans())
    actual_start = scheduled_start + timedelta(minutes=draw(st.integers(min_value=-30, max_value=30))) if has_actual_times else None
    actual_end = actual_start + timedelta(hours=draw(st.integers(min_value=1, max_value=8))) if actual_start else None
    
    return Job(
        id=draw(uuids()),
        leadId=draw(uuids()),
        technicianId=draw(uuids()),
        status=draw(st.sampled_from(list(JobStatus))),
        scheduledStart=scheduled_start,
        scheduledEnd=scheduled_end,
        actualStart=actual_start,
        actualEnd=actual_end,
        diagnosis=draw(st.one_of(st.none(), diagnoses())),
        partsUsed=draw(st.lists(parts(), min_size=0, max_size=5)),
        laborHours=draw(st.floats(min_value=0.5, max_value=8.0)),
        totalCost=draw(st.floats(min_value=50.0, max_value=5000.0)),
        customerSignature=draw(st.one_of(st.none(), st.text(min_size=10, max_size=100))),
        photos=draw(st.lists(st.text(min_size=10, max_size=100), min_size=0, max_size=10)),
        notes=draw(st.text(min_size=0, max_size=500)),
        carbonFootprint=draw(st.one_of(st.none(), carbon_footprints())),
    )


# ============================================================================
# Conversation Model Strategies
# ============================================================================


@st.composite
def intents(draw) -> Intent:
    """Generate valid Intent instances."""
    return Intent(
        name=draw(st.sampled_from(["JOB_COMPLETION", "LEAD_INTAKE", "DIAGNOSIS", "PARTS_QUERY", "SCHEDULING"])),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        parameters=draw(st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=50), min_size=0, max_size=5)),
    )


@st.composite
def entities(draw) -> Entity:
    """Generate valid Entity instances."""
    start = draw(st.integers(min_value=0, max_value=100))
    end = start + draw(st.integers(min_value=1, max_value=50))
    
    return Entity(
        type=draw(st.sampled_from(["PART_NUMBER", "TECHNICIAN_NAME", "CUSTOMER_NAME", "DATE", "TIME"])),
        value=draw(st.text(min_size=1, max_size=50)),
        confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
        span=(start, end),
    )


@st.composite
def conversation_turns(draw) -> ConversationTurn:
    """Generate valid ConversationTurn instances."""
    return ConversationTurn(
        speaker=draw(st.sampled_from(["user", "agent"])),
        content=draw(st.text(min_size=10, max_size=500)),
        timestamp=draw(datetimes_recent(min_days_ago=1, max_days_ago=0)),
        agent=draw(st.one_of(st.none(), st.sampled_from(["intake", "diagnostic", "fulfillment"]))),
        actions=draw(st.lists(st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=50)), min_size=0, max_size=3)),
    )


@st.composite
def conversation_contexts(draw) -> ConversationContext:
    """Generate valid ConversationContext instances."""
    return ConversationContext(
        sessionId=draw(uuids()),
        userId=draw(uuids()),
        userRole=draw(st.sampled_from(list(UserRole))),
        currentIntent=draw(st.one_of(st.none(), intents())),
        entities=draw(st.lists(entities(), min_size=0, max_size=5)),
        history=draw(st.lists(conversation_turns(), min_size=0, max_size=10)),
        state=draw(st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=50), min_size=0, max_size=5)),
        metadata={
            "startTime": draw(datetimes_recent(min_days_ago=1, max_days_ago=0)).timestamp(),
            "turnCount": draw(st.integers(min_value=0, max_value=50)),
            "activeAgents": draw(st.lists(st.sampled_from(["intake", "diagnostic", "fulfillment"]), min_size=0, max_size=3)),
        },
    )


# ============================================================================
# MCP Model Strategies
# ============================================================================


@st.composite
def mcp_errors(draw) -> MCPError:
    """Generate valid MCPError instances."""
    return MCPError(
        code=draw(st.integers(min_value=-32768, max_value=-32000)),
        message=draw(st.text(min_size=10, max_size=200)),
        data=draw(st.one_of(st.none(), st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=50)))),
    )


@st.composite
def mcp_tool_calls(draw) -> MCPToolCall:
    """Generate valid MCPToolCall instances."""
    return MCPToolCall(
        id=draw(uuids()),
        serverId=draw(st.sampled_from(["filesystem", "database", "inventree", "partdb", "kicost"])),
        toolName=draw(st.text(min_size=5, max_size=50)),
        parameters=draw(st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=50), min_size=0, max_size=5)),
        result=draw(st.one_of(st.none(), st.text(min_size=10, max_size=200))),
        error=draw(st.one_of(st.none(), mcp_errors())),
        timestamp=draw(datetimes_recent(min_days_ago=1, max_days_ago=0)),
        duration=draw(st.integers(min_value=10, max_value=5000)),
        agentId=draw(st.sampled_from(["intake", "diagnostic", "fulfillment"])),
    )


# ============================================================================
# Parts and Inventory Model Strategies
# ============================================================================


@st.composite
def parts_recommendations(draw) -> PartsRecommendation:
    """Generate valid PartsRecommendation instances."""
    primary_parts = draw(st.lists(parts(), min_size=1, max_size=3))
    
    return PartsRecommendation(
        primary=primary_parts,
        alternatives=draw(st.lists(st.lists(parts(), min_size=1, max_size=3), min_size=0, max_size=3)),
        totalCost=sum(p.unitCost * p.quantity for p in primary_parts),
        availability=draw(st.sampled_from(list(Availability))),
        distributorOptions=draw(st.lists(
            st.fixed_dictionaries({
                "distributor": st.sampled_from(["digikey", "mouser", "arrow", "newark", "tme"]),
                "price": st.floats(min_value=1.0, max_value=1000.0),
                "leadTime": st.integers(min_value=0, max_value=30),
                "quantity": st.integers(min_value=1, max_value=100),
            }),
            min_size=0,
            max_size=5,
        )),
    )


@st.composite
def equipment_infos(draw) -> EquipmentInfo:
    """Generate valid EquipmentInfo instances."""
    return EquipmentInfo(
        manufacturer=draw(st.sampled_from(["Honeywell", "Carrier", "Trane", "Lennox", "Rheem"])),
        model=draw(st.text(alphabet=st.characters(whitelist_categories=("Lu", "Nd")), min_size=5, max_size=20)),
        serialNumber=draw(st.one_of(st.none(), st.text(alphabet=st.characters(whitelist_categories=("Lu", "Nd")), min_size=8, max_size=20))),
        type=draw(st.sampled_from(["Air Conditioner", "Furnace", "Heat Pump", "Thermostat"])),
        specifications=draw(st.dictionaries(st.text(min_size=1, max_size=20), st.text(min_size=1, max_size=50), min_size=0, max_size=5)),
    )


# ============================================================================
# Schedule Model Strategies
# ============================================================================


@st.composite
def job_assignments(draw) -> JobAssignment:
    """Generate valid JobAssignment instances."""
    scheduled_start = draw(datetimes_future(min_days_ahead=0, max_days_ahead=30))
    scheduled_end = scheduled_start + timedelta(hours=draw(st.integers(min_value=1, max_value=8)))
    
    return JobAssignment(
        jobId=draw(uuids()),
        technicianId=draw(uuids()),
        scheduledStart=scheduled_start,
        scheduledEnd=scheduled_end,
        estimatedTravelTime=draw(st.integers(min_value=0, max_value=120)),
    )


@st.composite
def routes(draw) -> Route:
    """Generate valid Route instances."""
    assignments = draw(st.lists(job_assignments(), min_size=1, max_size=10))
    
    return Route(
        technicianId=draw(uuids()),
        assignments=assignments,
        totalDistance=draw(st.floats(min_value=0.0, max_value=500.0)),
        totalDuration=draw(st.integers(min_value=60, max_value=600)),
    )


@st.composite
def schedules(draw) -> Schedule:
    """Generate valid Schedule instances."""
    assignments = draw(st.lists(job_assignments(), min_size=1, max_size=20))
    routes_list = draw(st.lists(routes(), min_size=1, max_size=5))
    
    return Schedule(
        assignments=assignments,
        routes=routes_list,
        estimatedCompletionTime=draw(st.integers(min_value=60, max_value=600)),
        utilizationRate=draw(st.floats(min_value=0.0, max_value=1.0)),
    )


# ============================================================================
# Database Entity Model Strategies
# ============================================================================


@st.composite
def customers(draw) -> Customer:
    """Generate valid Customer instances."""
    created = draw(datetimes_recent(min_days_ago=365, max_days_ago=0))
    updated = created + timedelta(days=draw(st.integers(min_value=0, max_value=30)))
    
    return Customer(
        id=draw(uuids()),
        name=draw(st.text(min_size=3, max_size=100)),
        email=draw(st.one_of(st.none(), emails())),
        phone=draw(st.one_of(st.none(), phone_numbers())),
        address=draw(st.one_of(st.none(), st.text(min_size=10, max_size=200))),
        city=draw(st.one_of(st.none(), st.text(min_size=3, max_size=50))),
        state=draw(st.one_of(st.none(), st.sampled_from(["CA", "NY", "TX", "FL", "IL", "PA", "OH"]))),
        zipCode=draw(st.one_of(st.none(), st.text(alphabet=st.characters(whitelist_categories=("Nd",)), min_size=5, max_size=5))),
        createdAt=created,
        updatedAt=updated,
    )


@st.composite
def technicians(draw) -> Technician:
    """Generate valid Technician instances."""
    created = draw(datetimes_recent(min_days_ago=365, max_days_ago=0))
    updated = created + timedelta(days=draw(st.integers(min_value=0, max_value=30)))
    
    return Technician(
        id=draw(uuids()),
        name=draw(st.text(min_size=3, max_size=100)),
        email=draw(emails()),
        phone=draw(st.one_of(st.none(), phone_numbers())),
        skills=draw(st.lists(st.sampled_from(["HVAC", "Electrical", "Plumbing", "Diagnostics"]), min_size=1, max_size=4)),
        status=draw(st.sampled_from(list(TechnicianStatus))),
        currentLocationLat=draw(st.one_of(st.none(), st.floats(min_value=-90, max_value=90))),
        currentLocationLng=draw(st.one_of(st.none(), st.floats(min_value=-180, max_value=180))),
        createdAt=created,
        updatedAt=updated,
    )
