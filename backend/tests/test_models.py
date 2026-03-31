"""
Unit tests for Pydantic data models
Tests validation rules, serialization, and deserialization
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from core.models import (
    # Enums
    LeadSource, LeadStatus, Urgency, JobStatus, JobPriority,
    TechnicianStatus, ConversationChannel, ConversationStatus,
    # Customer models
    Customer, CustomerCreate, CustomerUpdate,
    # Technician models
    Technician, TechnicianCreate, TechnicianUpdate,
    # Lead models
    LeadDB, LeadCreate, LeadUpdate,
    # Job models
    JobDB, JobCreate, JobUpdate,
    # Part models
    PartDB, PartCreate, PartUpdate,
    # Conversation models
    ConversationDB, ConversationCreate, ConversationUpdate,
)


class TestCustomerModels:
    """Test suite for Customer models."""

    def test_customer_create_valid(self):
        """Test creating a valid customer."""
        customer = CustomerCreate(
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
            address="123 Main St",
            city="Springfield",
            state="IL",
            zip_code="62701"
        )
        assert customer.name == "John Doe"
        assert customer.email == "john@example.com"
        assert customer.phone == "555-1234"

    def test_customer_create_minimal(self):
        """Test creating customer with minimal required fields."""
        customer = CustomerCreate(name="Jane Doe")
        assert customer.name == "Jane Doe"
        assert customer.email is None
        assert customer.phone is None

    def test_customer_invalid_email(self):
        """Test customer creation with invalid email."""
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate(
                name="John Doe",
                email="invalid-email"
            )
        assert "Invalid email format" in str(exc_info.value)

    def test_customer_serialization(self):
        """Test customer model serialization."""
        customer = Customer(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
            address="123 Main St",
            city="Springfield",
            state="IL",
            zip_code="62701",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        data = customer.model_dump()
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        assert "id" in data
        assert "created_at" in data

    def test_customer_update_partial(self):
        """Test partial customer update."""
        update = CustomerUpdate(email="newemail@example.com")
        assert update.email == "newemail@example.com"
        assert update.name is None  # Other fields remain None


class TestTechnicianModels:
    """Test suite for Technician models."""

    def test_technician_create_valid(self):
        """Test creating a valid technician."""
        tech = TechnicianCreate(
            name="Bob Smith",
            email="bob@example.com",
            phone="555-5678",
            skills=["plumbing", "hvac"],
            status=TechnicianStatus.AVAILABLE
        )
        assert tech.name == "Bob Smith"
        assert tech.email == "bob@example.com"
        assert len(tech.skills) == 2
        assert tech.status == TechnicianStatus.AVAILABLE

    def test_technician_invalid_email(self):
        """Test technician creation with invalid email."""
        with pytest.raises(ValidationError) as exc_info:
            TechnicianCreate(
                name="Bob Smith",
                email="invalid-email"
            )
        assert "Invalid email format" in str(exc_info.value)

    def test_technician_location_validation(self):
        """Test technician location coordinate validation."""
        # Valid coordinates
        tech = TechnicianCreate(
            name="Bob Smith",
            email="bob@example.com",
            current_location_lat=40.7128,
            current_location_lng=-74.0060
        )
        assert tech.current_location_lat == 40.7128
        assert tech.current_location_lng == -74.0060

        # Invalid latitude (> 90)
        with pytest.raises(ValidationError):
            TechnicianCreate(
                name="Bob Smith",
                email="bob@example.com",
                current_location_lat=91.0
            )

        # Invalid longitude (< -180)
        with pytest.raises(ValidationError):
            TechnicianCreate(
                name="Bob Smith",
                email="bob@example.com",
                current_location_lng=-181.0
            )

    def test_technician_status_enum(self):
        """Test technician status enum values."""
        assert TechnicianStatus.AVAILABLE.value == "available"
        assert TechnicianStatus.BUSY.value == "busy"
        assert TechnicianStatus.OFFLINE.value == "offline"


class TestLeadModels:
    """Test suite for Lead models."""

    def test_lead_create_valid(self):
        """Test creating a valid lead."""
        lead = LeadCreate(
            customer_id="123e4567-e89b-12d3-a456-426614174000",
            source=LeadSource.VOICE,
            urgency=Urgency.URGENT,
            service_type="plumbing",
            description="Leaking pipe",
            confidence_score=0.95,
            status=LeadStatus.NEW
        )
        assert lead.source == LeadSource.VOICE
        assert lead.urgency == Urgency.URGENT
        assert lead.confidence_score == 0.95

    def test_lead_confidence_score_validation(self):
        """Test lead confidence score validation (0-1)."""
        # Valid score
        lead = LeadCreate(
            source=LeadSource.WEB,
            urgency=Urgency.ROUTINE,
            confidence_score=0.75
        )
        assert lead.confidence_score == 0.75

        # Invalid score (> 1)
        with pytest.raises(ValidationError):
            LeadCreate(
                source=LeadSource.WEB,
                urgency=Urgency.ROUTINE,
                confidence_score=1.5
            )

        # Invalid score (< 0)
        with pytest.raises(ValidationError):
            LeadCreate(
                source=LeadSource.WEB,
                urgency=Urgency.ROUTINE,
                confidence_score=-0.1
            )

    def test_lead_source_enum(self):
        """Test lead source enum values."""
        assert LeadSource.VOICE.value == "voice"
        assert LeadSource.SMS.value == "sms"
        assert LeadSource.WEB.value == "web"

    def test_lead_urgency_enum(self):
        """Test urgency enum values."""
        assert Urgency.EMERGENCY.value == "emergency"
        assert Urgency.URGENT.value == "urgent"
        assert Urgency.ROUTINE.value == "routine"


class TestJobModels:
    """Test suite for Job models."""

    def test_job_create_valid(self):
        """Test creating a valid job."""
        now = datetime.now()
        job = JobCreate(
            customer_id="123e4567-e89b-12d3-a456-426614174000",
            technician_id="223e4567-e89b-12d3-a456-426614174000",
            title="Fix water heater",
            description="Water heater not heating",
            service_type="plumbing",
            priority=JobPriority.HIGH,
            status=JobStatus.SCHEDULED,
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2)
        )
        assert job.title == "Fix water heater"
        assert job.priority == JobPriority.HIGH
        assert job.status == JobStatus.SCHEDULED

    def test_job_scheduled_end_validation(self):
        """Test job scheduled_end must be after scheduled_start."""
        now = datetime.now()
        
        # Valid: end after start
        job = JobCreate(
            customer_id="123e4567-e89b-12d3-a456-426614174000",
            title="Fix water heater",
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=2)
        )
        assert job.scheduled_end > job.scheduled_start

        # Invalid: end before start
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(
                customer_id="123e4567-e89b-12d3-a456-426614174000",
                title="Fix water heater",
                scheduled_start=now,
                scheduled_end=now - timedelta(hours=1)
            )
        assert "scheduled_end must be after scheduled_start" in str(exc_info.value)

    def test_job_priority_enum(self):
        """Test job priority enum values."""
        assert JobPriority.EMERGENCY.value == "emergency"
        assert JobPriority.HIGH.value == "high"
        assert JobPriority.NORMAL.value == "normal"
        assert JobPriority.LOW.value == "low"

    def test_job_status_enum(self):
        """Test job status enum values."""
        assert JobStatus.SCHEDULED.value == "scheduled"
        assert JobStatus.IN_PROGRESS.value == "in-progress"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.CANCELLED.value == "cancelled"

    def test_job_first_time_fix_default(self):
        """Test job first_time_fix defaults to False."""
        job = JobCreate(
            customer_id="123e4567-e89b-12d3-a456-426614174000",
            title="Fix water heater"
        )
        assert job.first_time_fix is False


class TestPartModels:
    """Test suite for Part models."""

    def test_part_create_valid(self):
        """Test creating a valid part."""
        part = PartCreate(
            part_number="WH-123",
            name="Water Heater Element",
            description="Heating element for water heater",
            manufacturer="Acme Corp",
            category="plumbing",
            quantity_available=50,
            unit_price=29.99,
            reorder_level=10
        )
        assert part.part_number == "WH-123"
        assert part.name == "Water Heater Element"
        assert part.quantity_available == 50
        assert part.unit_price == 29.99

    def test_part_quantity_validation(self):
        """Test part quantity must be non-negative."""
        # Valid quantity
        part = PartCreate(
            part_number="WH-123",
            name="Water Heater Element",
            quantity_available=0
        )
        assert part.quantity_available == 0

        # Invalid quantity (negative)
        with pytest.raises(ValidationError):
            PartCreate(
                part_number="WH-123",
                name="Water Heater Element",
                quantity_available=-1
            )

    def test_part_price_validation(self):
        """Test part unit_price must be non-negative."""
        # Valid price
        part = PartCreate(
            part_number="WH-123",
            name="Water Heater Element",
            unit_price=0.0
        )
        assert part.unit_price == 0.0

        # Invalid price (negative)
        with pytest.raises(ValidationError):
            PartCreate(
                part_number="WH-123",
                name="Water Heater Element",
                unit_price=-10.0
            )

    def test_part_defaults(self):
        """Test part default values."""
        part = PartCreate(
            part_number="WH-123",
            name="Water Heater Element"
        )
        assert part.quantity_available == 0
        assert part.reorder_level == 10


class TestConversationModels:
    """Test suite for Conversation models."""

    def test_conversation_create_valid(self):
        """Test creating a valid conversation."""
        conv = ConversationCreate(
            session_id="sess-123",
            customer_id="123e4567-e89b-12d3-a456-426614174000",
            channel=ConversationChannel.VOICE,
            status=ConversationStatus.ACTIVE,
            context={"intent": "job_completion"}
        )
        assert conv.session_id == "sess-123"
        assert conv.channel == ConversationChannel.VOICE
        assert conv.status == ConversationStatus.ACTIVE
        assert conv.context["intent"] == "job_completion"

    def test_conversation_channel_enum(self):
        """Test conversation channel enum values."""
        assert ConversationChannel.VOICE.value == "voice"
        assert ConversationChannel.SMS.value == "sms"
        assert ConversationChannel.WEB.value == "web"

    def test_conversation_status_enum(self):
        """Test conversation status enum values."""
        assert ConversationStatus.ACTIVE.value == "active"
        assert ConversationStatus.COMPLETED.value == "completed"
        assert ConversationStatus.ABANDONED.value == "abandoned"

    def test_conversation_defaults(self):
        """Test conversation default values."""
        conv = ConversationCreate(
            session_id="sess-123",
            channel=ConversationChannel.WEB
        )
        assert conv.status == ConversationStatus.ACTIVE
        assert conv.context is None


class TestModelSerialization:
    """Test suite for model serialization/deserialization."""

    def test_customer_json_serialization(self):
        """Test customer JSON serialization."""
        customer = Customer(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="John Doe",
            email="john@example.com",
            phone="555-1234",
            address="123 Main St",
            city="Springfield",
            state="IL",
            zip_code="62701",
            created_at=datetime(2026, 3, 31, 12, 0, 0),
            updated_at=datetime(2026, 3, 31, 12, 0, 0)
        )
        
        # Serialize to dict
        data = customer.model_dump()
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"
        
        # Serialize to JSON
        json_str = customer.model_dump_json()
        assert "John Doe" in json_str
        assert "john@example.com" in json_str

    def test_job_json_deserialization(self):
        """Test job JSON deserialization."""
        json_data = {
            "customerId": "123e4567-e89b-12d3-a456-426614174000",
            "title": "Fix water heater",
            "priority": "high",
            "status": "scheduled",
            "firstTimeFix": False
        }
        
        job = JobCreate(**json_data)
        assert job.customer_id == "123e4567-e89b-12d3-a456-426614174000"
        assert job.title == "Fix water heater"
        assert job.priority == JobPriority.HIGH
        assert job.first_time_fix is False

    def test_alias_handling(self):
        """Test camelCase alias handling."""
        # Create with snake_case
        lead = LeadCreate(
            customer_id="123",
            source=LeadSource.VOICE,
            urgency=Urgency.URGENT,
            service_type="plumbing",
            confidence_score=0.95
        )
        
        # Serialize with aliases (camelCase)
        data = lead.model_dump(by_alias=True)
        assert "customerId" in data
        assert "serviceType" in data
        assert "confidenceScore" in data
        
        # Deserialize from camelCase
        lead2 = LeadCreate(**{
            "customerId": "456",
            "source": "web",
            "urgency": "routine",
            "serviceType": "hvac",
            "confidenceScore": 0.85
        })
        assert lead2.customer_id == "456"
        assert lead2.service_type == "hvac"
        assert lead2.confidence_score == 0.85


class TestModelValidation:
    """Test suite for model validation rules."""

    def test_required_fields(self):
        """Test required field validation."""
        # Customer requires name
        with pytest.raises(ValidationError) as exc_info:
            CustomerCreate()
        assert "name" in str(exc_info.value)

        # Technician requires name and email
        with pytest.raises(ValidationError) as exc_info:
            TechnicianCreate(name="Bob")
        assert "email" in str(exc_info.value)

        # Job requires customer_id and title
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(customer_id="123")
        assert "title" in str(exc_info.value)

    def test_string_length_validation(self):
        """Test string length validation."""
        # Name too long (> 255 chars)
        with pytest.raises(ValidationError):
            CustomerCreate(name="A" * 256)

        # Valid name length
        customer = CustomerCreate(name="A" * 255)
        assert len(customer.name) == 255

    def test_enum_validation(self):
        """Test enum value validation."""
        # Valid enum value
        lead = LeadCreate(
            source=LeadSource.VOICE,
            urgency=Urgency.URGENT
        )
        assert lead.source == LeadSource.VOICE

        # Invalid enum value
        with pytest.raises(ValidationError):
            LeadCreate(
                source="invalid_source",
                urgency=Urgency.URGENT
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
