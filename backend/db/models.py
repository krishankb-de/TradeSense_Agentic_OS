"""SQLAlchemy ORM models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import relationship

from backend.db.session import Base


class Customer(Base):
    """Customer ORM model."""

    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(50))
    address = Column(Text)
    city = Column(String(100))
    state = Column(String(50))
    zip_code = Column(String(20))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    leads = relationship("Lead", back_populates="customer")
    jobs = relationship("Job", back_populates="customer")
    conversations = relationship("Conversation", back_populates="customer")


class Technician(Base):
    """Technician ORM model."""

    __tablename__ = "technicians"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50))
    skills = Column(ARRAY(Text))
    status = Column(String(50), default="available")
    current_location_lat = Column(Float)
    current_location_lng = Column(Float)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    jobs = relationship("Job", back_populates="technician")
    conversations = relationship("Conversation", back_populates="technician")


class Lead(Base):
    """Lead ORM model."""

    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    source = Column(String(50), nullable=False)
    urgency = Column(String(50), nullable=False)
    service_type = Column(String(100))
    description = Column(Text)
    confidence_score = Column(Float)
    status = Column(String(50), default="new")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="leads")
    jobs = relationship("Job", back_populates="lead")


class Job(Base):
    """Job ORM model."""

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"))
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    technician_id = Column(UUID(as_uuid=True), ForeignKey("technicians.id", ondelete="SET NULL"))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    service_type = Column(String(100))
    priority = Column(String(50), default="normal")
    status = Column(String(50), default="scheduled")
    scheduled_start = Column(DateTime(timezone=True))
    scheduled_end = Column(DateTime(timezone=True))
    actual_start = Column(DateTime(timezone=True))
    actual_end = Column(DateTime(timezone=True))
    location_address = Column(Text)
    location_lat = Column(Float)
    location_lng = Column(Float)
    first_time_fix = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lead = relationship("Lead", back_populates="jobs")
    customer = relationship("Customer", back_populates="jobs")
    technician = relationship("Technician", back_populates="jobs")
    job_parts = relationship("JobPart", back_populates="job")
    conversations = relationship("Conversation", back_populates="job")


class Part(Base):
    """Part ORM model."""

    __tablename__ = "parts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    part_number = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    manufacturer = Column(String(255))
    category = Column(String(100))
    quantity_available = Column(Integer, default=0)
    unit_price = Column(Float)
    reorder_level = Column(Integer, default=10)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job_parts = relationship("JobPart", back_populates="part")


class JobPart(Base):
    """Job-Part association ORM model."""

    __tablename__ = "job_parts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    part_id = Column(UUID(as_uuid=True), ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    quantity_used = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    job = relationship("Job", back_populates="job_parts")
    part = relationship("Part", back_populates="job_parts")


class Conversation(Base):
    """Conversation ORM model."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(String(255), unique=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    technician_id = Column(UUID(as_uuid=True), ForeignKey("technicians.id", ondelete="SET NULL"))
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"))
    channel = Column(String(50), nullable=False)
    status = Column(String(50), default="active")
    context = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    customer = relationship("Customer", back_populates="conversations")
    technician = relationship("Technician", back_populates="conversations")
    job = relationship("Job", back_populates="conversations")
    turns = relationship("ConversationTurn", back_populates="conversation")
    mcp_tool_calls = relationship("MCPToolCall", back_populates="conversation")


class ConversationTurn(Base):
    """Conversation turn ORM model."""

    __tablename__ = "conversation_turns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    speaker = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    intent = Column(String(100))
    confidence_score = Column(Float)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="turns")


class AuditLog(Base):
    """Audit log ORM model (partitioned)."""

    __tablename__ = "audit_logs"
    __table_args__ = {"postgresql_partition_by": "RANGE (created_at)"}

    id = Column(UUID(as_uuid=True), default=uuid4)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    action = Column(String(50), nullable=False)
    user_id = Column(UUID(as_uuid=True))
    user_type = Column(String(50))
    changes = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, primary_key=True)


class MCPToolCall(Base):
    """MCP tool call ORM model."""

    __tablename__ = "mcp_tool_calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="SET NULL"))
    tool_name = Column(String(255), nullable=False)
    tool_server = Column(String(255), nullable=False)
    input_params = Column(JSONB)
    output_result = Column(JSONB)
    execution_time_ms = Column(Integer)
    status = Column(String(50), default="success")
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="mcp_tool_calls")
