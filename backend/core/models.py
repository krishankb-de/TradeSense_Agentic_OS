"""Shared Pydantic models for cross-component data exchange."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================


class LeadSource(str, Enum):
    """Lead source types."""

    VOICE = "voice"
    SMS = "sms"
    WEB = "web"


class LeadStatus(str, Enum):
    """Lead status types."""

    NEW = "new"
    TRIAGED = "triaged"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Urgency(str, Enum):
    """Urgency levels."""

    EMERGENCY = "emergency"
    URGENT = "urgent"
    ROUTINE = "routine"


class JobStatus(str, Enum):
    """Job status types."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PartSource(str, Enum):
    """Part source types."""

    INVENTORY = "inventory"
    ORDERED = "ordered"
    CUSTOMER_SUPPLIED = "customer-supplied"


class Complexity(str, Enum):
    """Diagnosis complexity levels."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class Availability(str, Enum):
    """Parts availability status."""

    IN_STOCK = "in-stock"
    ORDER_REQUIRED = "order-required"
    UNAVAILABLE = "unavailable"


class ComplianceStatus(str, Enum):
    """Carbon compliance status."""

    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non-compliant"


class UserRole(str, Enum):
    """User role types."""

    TECHNICIAN = "technician"
    CUSTOMER = "customer"
    DISPATCHER = "dispatcher"
    ADMIN = "admin"


# ============================================================================
# Base Models
# ============================================================================


class GeoLocation(BaseModel):
    """Geographic location information."""

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str
    city: str
    state: str
    zip_code: str = Field(..., alias="zipCode")

    class Config:
        populate_by_name = True


class Part(BaseModel):
    """Part information."""

    id: str
    name: str
    manufacturer: str
    model_number: str = Field(..., alias="modelNumber")
    quantity: int = Field(..., gt=0)
    unit_cost: float = Field(..., alias="unitCost", ge=0)
    source: PartSource

    class Config:
        populate_by_name = True


# ============================================================================
# Lead Models
# ============================================================================


class Lead(BaseModel):
    """Lead information."""

    id: str
    customer_id: str = Field(..., alias="customerId")
    source: LeadSource
    status: LeadStatus
    issue_description: str = Field(..., alias="issueDescription")
    urgency: Urgency
    service_type: str = Field(..., alias="serviceType")
    location: GeoLocation
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
    assigned_technician_id: Optional[str] = Field(None, alias="assignedTechnicianId")
    estimated_value: float = Field(..., alias="estimatedValue", ge=0)

    class Config:
        populate_by_name = True


class TriageResult(BaseModel):
    """Triage classification result."""

    service_type: str = Field(..., alias="serviceType")
    estimated_duration: int = Field(..., alias="estimatedDuration", gt=0)
    required_skills: List[str] = Field(..., alias="requiredSkills")
    suggested_technicians: List[str] = Field(..., alias="suggestedTechnicians")
    priority: int = Field(..., ge=1, le=10)
    confidence: float = Field(..., ge=0, le=1)

    class Config:
        populate_by_name = True


# ============================================================================
# Job Models
# ============================================================================


class Diagnosis(BaseModel):
    """Diagnostic information."""

    issue_type: str = Field(..., alias="issueType")
    root_cause: str = Field(..., alias="rootCause")
    confidence: float = Field(..., ge=0, le=1)
    required_parts: List[Part] = Field(..., alias="requiredParts")
    estimated_repair_time: int = Field(..., alias="estimatedRepairTime", gt=0)
    complexity: Complexity
    reasoning_steps: List[str] = Field(default_factory=list, alias="reasoningSteps")

    class Config:
        populate_by_name = True


class CarbonFootprint(BaseModel):
    """Carbon footprint information."""

    total_emissions: float = Field(..., alias="totalEmissions", ge=0)
    breakdown: List[Dict[str, Any]]
    compliance_status: ComplianceStatus = Field(..., alias="complianceStatus")
    recommendations: List[str]
    data_sources: List[str] = Field(..., alias="dataSources")

    class Config:
        populate_by_name = True


class Job(BaseModel):
    """Job information."""

    id: str
    lead_id: str = Field(..., alias="leadId")
    technician_id: str = Field(..., alias="technicianId")
    status: JobStatus
    scheduled_start: datetime = Field(..., alias="scheduledStart")
    scheduled_end: datetime = Field(..., alias="scheduledEnd")
    actual_start: Optional[datetime] = Field(None, alias="actualStart")
    actual_end: Optional[datetime] = Field(None, alias="actualEnd")
    diagnosis: Optional[Diagnosis] = None
    parts_used: List[Part] = Field(default_factory=list, alias="partsUsed")
    labor_hours: float = Field(..., alias="laborHours", ge=0)
    total_cost: float = Field(..., alias="totalCost", ge=0)
    customer_signature: Optional[str] = Field(None, alias="customerSignature")
    photos: List[str] = Field(default_factory=list)
    notes: str = ""
    carbon_footprint: Optional[CarbonFootprint] = Field(None, alias="carbonFootprint")

    @field_validator("scheduled_end")
    @classmethod
    def validate_scheduled_end(cls, v: datetime, info) -> datetime:
        """Validate scheduled_end is after scheduled_start."""
        if "scheduled_start" in info.data and v <= info.data["scheduled_start"]:
            raise ValueError("scheduled_end must be after scheduled_start")
        return v

    class Config:
        populate_by_name = True


# ============================================================================
# Conversation Models
# ============================================================================


class Intent(BaseModel):
    """Intent classification."""

    name: str
    confidence: float = Field(..., ge=0, le=1)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Entity(BaseModel):
    """Named entity."""

    type: str
    value: str
    confidence: float = Field(..., ge=0, le=1)
    span: tuple[int, int]


class ConversationTurn(BaseModel):
    """Single conversation turn."""

    speaker: str
    content: str
    timestamp: datetime
    agent: Optional[str] = None
    actions: List[Dict[str, Any]] = Field(default_factory=list)


class ConversationContext(BaseModel):
    """Conversation context and state."""

    session_id: str = Field(..., alias="sessionId")
    user_id: str = Field(..., alias="userId")
    user_role: UserRole = Field(..., alias="userRole")
    current_intent: Optional[Intent] = Field(None, alias="currentIntent")
    entities: List[Entity] = Field(default_factory=list)
    history: List[ConversationTurn] = Field(default_factory=list)
    state: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


# ============================================================================
# MCP Models
# ============================================================================


class MCPError(BaseModel):
    """MCP error information."""

    code: int
    message: str
    data: Optional[Dict[str, Any]] = None


class MCPToolCall(BaseModel):
    """MCP tool call record."""

    id: str
    server_id: str = Field(..., alias="serverId")
    tool_name: str = Field(..., alias="toolName")
    parameters: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[MCPError] = None
    timestamp: datetime
    duration: int = Field(..., ge=0)
    agent_id: str = Field(..., alias="agentId")

    class Config:
        populate_by_name = True


# ============================================================================
# Parts and Inventory Models
# ============================================================================


class PartsRecommendation(BaseModel):
    """Parts recommendation with alternatives."""

    primary: List[Part]
    alternatives: List[List[Part]]
    total_cost: float = Field(..., alias="totalCost", ge=0)
    availability: Availability
    distributor_options: List[Dict[str, Any]] = Field(
        default_factory=list, alias="distributorOptions"
    )

    class Config:
        populate_by_name = True


class EquipmentInfo(BaseModel):
    """Equipment information extracted from images."""

    manufacturer: str
    model: str
    serial_number: Optional[str] = Field(None, alias="serialNumber")
    type: str
    specifications: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True


# ============================================================================
# Schedule Models
# ============================================================================


class JobAssignment(BaseModel):
    """Job assignment to technician."""

    job_id: str = Field(..., alias="jobId")
    technician_id: str = Field(..., alias="technicianId")
    scheduled_start: datetime = Field(..., alias="scheduledStart")
    scheduled_end: datetime = Field(..., alias="scheduledEnd")
    estimated_travel_time: int = Field(..., alias="estimatedTravelTime", ge=0)

    class Config:
        populate_by_name = True


class Route(BaseModel):
    """Optimized route for technician."""

    technician_id: str = Field(..., alias="technicianId")
    assignments: List[JobAssignment]
    total_distance: float = Field(..., alias="totalDistance", ge=0)
    total_duration: int = Field(..., alias="totalDuration", ge=0)

    class Config:
        populate_by_name = True


class Schedule(BaseModel):
    """Optimized schedule."""

    assignments: List[JobAssignment]
    routes: List[Route]
    estimated_completion_time: int = Field(..., alias="estimatedCompletionTime", ge=0)
    utilization_rate: float = Field(..., alias="utilizationRate", ge=0, le=1)

    class Config:
        populate_by_name = True
