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


# ============================================================================
# Database Entity Models
# ============================================================================


class CustomerBase(BaseModel):
    """Base customer model."""

    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20, alias="zipCode")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v

    class Config:
        populate_by_name = True


class CustomerCreate(CustomerBase):
    """Customer creation model."""

    pass


class CustomerUpdate(BaseModel):
    """Customer update model (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = None
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20, alias="zipCode")

    class Config:
        populate_by_name = True


class Customer(CustomerBase):
    """Customer model with database fields."""

    id: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class TechnicianStatus(str, Enum):
    """Technician status types."""

    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


class TechnicianBase(BaseModel):
    """Base technician model."""

    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    skills: List[str] = Field(default_factory=list)
    status: TechnicianStatus = TechnicianStatus.AVAILABLE
    current_location_lat: Optional[float] = Field(None, ge=-90, le=90, alias="currentLocationLat")
    current_location_lng: Optional[float] = Field(None, ge=-180, le=180, alias="currentLocationLng")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if "@" not in v:
            raise ValueError("Invalid email format")
        return v

    class Config:
        populate_by_name = True


class TechnicianCreate(TechnicianBase):
    """Technician creation model."""

    pass


class TechnicianUpdate(BaseModel):
    """Technician update model (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    skills: Optional[List[str]] = None
    status: Optional[TechnicianStatus] = None
    current_location_lat: Optional[float] = Field(None, ge=-90, le=90, alias="currentLocationLat")
    current_location_lng: Optional[float] = Field(None, ge=-180, le=180, alias="currentLocationLng")

    class Config:
        populate_by_name = True


class Technician(TechnicianBase):
    """Technician model with database fields."""

    id: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class LeadBase(BaseModel):
    """Base lead model."""

    customer_id: Optional[str] = Field(None, alias="customerId")
    source: LeadSource
    urgency: Urgency
    service_type: Optional[str] = Field(None, max_length=100, alias="serviceType")
    description: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1, alias="confidenceScore")
    status: LeadStatus = LeadStatus.NEW

    class Config:
        populate_by_name = True


class LeadCreate(LeadBase):
    """Lead creation model."""

    pass


class LeadUpdate(BaseModel):
    """Lead update model (all fields optional)."""

    customer_id: Optional[str] = Field(None, alias="customerId")
    source: Optional[LeadSource] = None
    urgency: Optional[Urgency] = None
    service_type: Optional[str] = Field(None, max_length=100, alias="serviceType")
    description: Optional[str] = None
    confidence_score: Optional[float] = Field(None, ge=0, le=1, alias="confidenceScore")
    status: Optional[LeadStatus] = None

    class Config:
        populate_by_name = True


class LeadDB(LeadBase):
    """Lead model with database fields."""

    id: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class JobPriority(str, Enum):
    """Job priority levels."""

    EMERGENCY = "emergency"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class JobBase(BaseModel):
    """Base job model."""

    lead_id: Optional[str] = Field(None, alias="leadId")
    customer_id: str = Field(..., alias="customerId")
    technician_id: Optional[str] = Field(None, alias="technicianId")
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    service_type: Optional[str] = Field(None, max_length=100, alias="serviceType")
    priority: JobPriority = JobPriority.NORMAL
    status: JobStatus = JobStatus.SCHEDULED
    scheduled_start: Optional[datetime] = Field(None, alias="scheduledStart")
    scheduled_end: Optional[datetime] = Field(None, alias="scheduledEnd")
    actual_start: Optional[datetime] = Field(None, alias="actualStart")
    actual_end: Optional[datetime] = Field(None, alias="actualEnd")
    location_address: Optional[str] = Field(None, alias="locationAddress")
    location_lat: Optional[float] = Field(None, ge=-90, le=90, alias="locationLat")
    location_lng: Optional[float] = Field(None, ge=-180, le=180, alias="locationLng")
    first_time_fix: bool = Field(False, alias="firstTimeFix")

    @field_validator("scheduled_end")
    @classmethod
    def validate_scheduled_end(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate scheduled_end is after scheduled_start."""
        if v and "scheduled_start" in info.data and info.data["scheduled_start"]:
            if v <= info.data["scheduled_start"]:
                raise ValueError("scheduled_end must be after scheduled_start")
        return v

    class Config:
        populate_by_name = True


class JobCreate(JobBase):
    """Job creation model."""

    pass


class JobUpdate(BaseModel):
    """Job update model (all fields optional)."""

    lead_id: Optional[str] = Field(None, alias="leadId")
    customer_id: Optional[str] = Field(None, alias="customerId")
    technician_id: Optional[str] = Field(None, alias="technicianId")
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    service_type: Optional[str] = Field(None, max_length=100, alias="serviceType")
    priority: Optional[JobPriority] = None
    status: Optional[JobStatus] = None
    scheduled_start: Optional[datetime] = Field(None, alias="scheduledStart")
    scheduled_end: Optional[datetime] = Field(None, alias="scheduledEnd")
    actual_start: Optional[datetime] = Field(None, alias="actualStart")
    actual_end: Optional[datetime] = Field(None, alias="actualEnd")
    location_address: Optional[str] = Field(None, alias="locationAddress")
    location_lat: Optional[float] = Field(None, ge=-90, le=90, alias="locationLat")
    location_lng: Optional[float] = Field(None, ge=-180, le=180, alias="locationLng")
    first_time_fix: Optional[bool] = Field(None, alias="firstTimeFix")

    class Config:
        populate_by_name = True


class JobDB(JobBase):
    """Job model with database fields."""

    id: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class PartBase(BaseModel):
    """Base part model."""

    part_number: str = Field(..., min_length=1, max_length=100, alias="partNumber")
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    manufacturer: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    quantity_available: int = Field(0, ge=0, alias="quantityAvailable")
    unit_price: Optional[float] = Field(None, ge=0, alias="unitPrice")
    reorder_level: int = Field(10, ge=0, alias="reorderLevel")

    class Config:
        populate_by_name = True


class PartCreate(PartBase):
    """Part creation model."""

    pass


class PartUpdate(BaseModel):
    """Part update model (all fields optional)."""

    part_number: Optional[str] = Field(None, min_length=1, max_length=100, alias="partNumber")
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    manufacturer: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    quantity_available: Optional[int] = Field(None, ge=0, alias="quantityAvailable")
    unit_price: Optional[float] = Field(None, ge=0, alias="unitPrice")
    reorder_level: Optional[int] = Field(None, ge=0, alias="reorderLevel")

    class Config:
        populate_by_name = True


class PartDB(PartBase):
    """Part model with database fields."""

    id: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class ConversationChannel(str, Enum):
    """Conversation channel types."""

    VOICE = "voice"
    SMS = "sms"
    WEB = "web"


class ConversationStatus(str, Enum):
    """Conversation status types."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ConversationBase(BaseModel):
    """Base conversation model."""

    session_id: str = Field(..., min_length=1, max_length=255, alias="sessionId")
    customer_id: Optional[str] = Field(None, alias="customerId")
    technician_id: Optional[str] = Field(None, alias="technicianId")
    job_id: Optional[str] = Field(None, alias="jobId")
    channel: ConversationChannel
    status: ConversationStatus = ConversationStatus.ACTIVE
    context: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class ConversationCreate(ConversationBase):
    """Conversation creation model."""

    pass


class ConversationUpdate(BaseModel):
    """Conversation update model (all fields optional)."""

    customer_id: Optional[str] = Field(None, alias="customerId")
    technician_id: Optional[str] = Field(None, alias="technicianId")
    job_id: Optional[str] = Field(None, alias="jobId")
    status: Optional[ConversationStatus] = None
    context: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class ConversationDB(ConversationBase):
    """Conversation model with database fields."""

    id: str
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    class Config:
        populate_by_name = True
        from_attributes = True
