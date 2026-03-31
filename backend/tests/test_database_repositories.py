"""Unit tests for database repositories."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.db.models import (
    Base,
    Customer,
    Technician,
    Lead,
    Job,
    Part,
    Conversation,
    ConversationTurn,
)
from backend.db.repositories import (
    CustomerRepository,
    TechnicianRepository,
    LeadRepository,
    JobRepository,
    PartRepository,
    ConversationRepository,
)


# Test database setup
@pytest.fixture(scope="function")
def db_session():
    """Create test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


# Customer Repository Tests
def test_customer_repository_create(db_session: Session):
    """Test customer creation."""
    repo = CustomerRepository(db_session)
    customer = repo.create(
        name="John Doe",
        email="john@example.com",
        phone="555-1234",
        city="New York",
        state="NY",
        zip_code="10001",
    )
    assert customer.id is not None
    assert customer.name == "John Doe"
    assert customer.email == "john@example.com"


def test_customer_repository_get_by_email(db_session: Session):
    """Test get customer by email."""
    repo = CustomerRepository(db_session)
    customer = repo.create(name="Jane Doe", email="jane@example.com")
    
    found = repo.get_by_email("jane@example.com")
    assert found is not None
    assert found.id == customer.id
    assert found.email == "jane@example.com"


def test_customer_repository_search_by_name(db_session: Session):
    """Test search customers by name."""
    repo = CustomerRepository(db_session)
    repo.create(name="John Smith", email="john@example.com")
    repo.create(name="Jane Smith", email="jane@example.com")
    repo.create(name="Bob Johnson", email="bob@example.com")
    
    results = repo.search_by_name("Smith")
    assert len(results) == 2
    assert all("Smith" in c.name for c in results)


# Technician Repository Tests
def test_technician_repository_create(db_session: Session):
    """Test technician creation."""
    repo = TechnicianRepository(db_session)
    tech = repo.create(
        name="Mike Tech",
        email="mike@example.com",
        skills=["HVAC", "Plumbing"],
        status="available",
    )
    assert tech.id is not None
    assert tech.name == "Mike Tech"
    assert "HVAC" in tech.skills


def test_technician_repository_get_by_status(db_session: Session):
    """Test get technicians by status."""
    repo = TechnicianRepository(db_session)
    repo.create(name="Tech 1", email="tech1@example.com", status="available")
    repo.create(name="Tech 2", email="tech2@example.com", status="busy")
    repo.create(name="Tech 3", email="tech3@example.com", status="available")
    
    available = repo.get_by_status("available")
    assert len(available) == 2
    assert all(t.status == "available" for t in available)


def test_technician_repository_get_by_skill(db_session: Session):
    """Test get technicians by skill."""
    repo = TechnicianRepository(db_session)
    repo.create(name="Tech 1", email="tech1@example.com", skills=["HVAC", "Electrical"])
    repo.create(name="Tech 2", email="tech2@example.com", skills=["Plumbing"])
    repo.create(name="Tech 3", email="tech3@example.com", skills=["HVAC"])
    
    hvac_techs = repo.get_by_skill("HVAC")
    assert len(hvac_techs) == 2


# Lead Repository Tests
def test_lead_repository_create(db_session: Session):
    """Test lead creation."""
    # Create customer first
    customer_repo = CustomerRepository(db_session)
    customer = customer_repo.create(name="Test Customer", email="test@example.com")
    
    # Create lead
    lead_repo = LeadRepository(db_session)
    lead = lead_repo.create(
        customer_id=customer.id,
        source="voice",
        urgency="urgent",
        service_type="HVAC Repair",
        description="AC not working",
        status="new",
    )
    assert lead.id is not None
    assert lead.urgency == "urgent"
    assert lead.source == "voice"


def test_lead_repository_get_by_urgency(db_session: Session):
    """Test get leads by urgency."""
    customer_repo = CustomerRepository(db_session)
    customer = customer_repo.create(name="Test Customer", email="test@example.com")
    
    lead_repo = LeadRepository(db_session)
    lead_repo.create(customer_id=customer.id, source="voice", urgency="emergency")
    lead_repo.create(customer_id=customer.id, source="sms", urgency="urgent")
    lead_repo.create(customer_id=customer.id, source="web", urgency="emergency")
    
    emergency_leads = lead_repo.get_by_urgency("emergency")
    assert len(emergency_leads) == 2


# Job Repository Tests
def test_job_repository_create(db_session: Session):
    """Test job creation."""
    # Create customer and technician
    customer_repo = CustomerRepository(db_session)
    customer = customer_repo.create(name="Test Customer", email="test@example.com")
    
    tech_repo = TechnicianRepository(db_session)
    tech = tech_repo.create(name="Test Tech", email="tech@example.com")
    
    # Create job
    job_repo = JobRepository(db_session)
    job = job_repo.create(
        customer_id=customer.id,
        technician_id=tech.id,
        title="HVAC Repair",
        description="Fix AC unit",
        priority="high",
        status="scheduled",
    )
    assert job.id is not None
    assert job.title == "HVAC Repair"
    assert job.priority == "high"


def test_job_repository_get_by_technician(db_session: Session):
    """Test get jobs by technician."""
    customer_repo = CustomerRepository(db_session)
    customer = customer_repo.create(name="Test Customer", email="test@example.com")
    
    tech_repo = TechnicianRepository(db_session)
    tech1 = tech_repo.create(name="Tech 1", email="tech1@example.com")
    tech2 = tech_repo.create(name="Tech 2", email="tech2@example.com")
    
    job_repo = JobRepository(db_session)
    job_repo.create(customer_id=customer.id, technician_id=tech1.id, title="Job 1")
    job_repo.create(customer_id=customer.id, technician_id=tech1.id, title="Job 2")
    job_repo.create(customer_id=customer.id, technician_id=tech2.id, title="Job 3")
    
    tech1_jobs = job_repo.get_by_technician(tech1.id)
    assert len(tech1_jobs) == 2


def test_job_repository_get_scheduled_between(db_session: Session):
    """Test get jobs scheduled between dates."""
    customer_repo = CustomerRepository(db_session)
    customer = customer_repo.create(name="Test Customer", email="test@example.com")
    
    job_repo = JobRepository(db_session)
    now = datetime.utcnow()
    
    job_repo.create(
        customer_id=customer.id,
        title="Job 1",
        scheduled_start=now + timedelta(days=1),
    )
    job_repo.create(
        customer_id=customer.id,
        title="Job 2",
        scheduled_start=now + timedelta(days=5),
    )
    job_repo.create(
        customer_id=customer.id,
        title="Job 3",
        scheduled_start=now + timedelta(days=10),
    )
    
    jobs = job_repo.get_scheduled_between(
        now,
        now + timedelta(days=7),
    )
    assert len(jobs) == 2


# Part Repository Tests
def test_part_repository_create(db_session: Session):
    """Test part creation."""
    repo = PartRepository(db_session)
    part = repo.create(
        part_number="HVAC-123",
        name="Air Filter",
        category="HVAC",
        quantity_available=50,
        unit_price=15.99,
        reorder_level=10,
    )
    assert part.id is not None
    assert part.part_number == "HVAC-123"
    assert part.quantity_available == 50


def test_part_repository_get_by_part_number(db_session: Session):
    """Test get part by part number."""
    repo = PartRepository(db_session)
    part = repo.create(part_number="TEST-001", name="Test Part")
    
    found = repo.get_by_part_number("TEST-001")
    assert found is not None
    assert found.id == part.id


def test_part_repository_get_low_stock(db_session: Session):
    """Test get parts with low stock."""
    repo = PartRepository(db_session)
    repo.create(part_number="P1", name="Part 1", quantity_available=5, reorder_level=10)
    repo.create(part_number="P2", name="Part 2", quantity_available=20, reorder_level=10)
    repo.create(part_number="P3", name="Part 3", quantity_available=8, reorder_level=10)
    
    low_stock = repo.get_low_stock()
    assert len(low_stock) == 2


def test_part_repository_update_quantity(db_session: Session):
    """Test update part quantity."""
    repo = PartRepository(db_session)
    part = repo.create(part_number="TEST-001", name="Test Part", quantity_available=100)
    
    # Subtract quantity
    updated = repo.update_quantity(part.id, -10)
    assert updated.quantity_available == 90
    
    # Add quantity
    updated = repo.update_quantity(part.id, 20)
    assert updated.quantity_available == 110


# Conversation Repository Tests
def test_conversation_repository_create(db_session: Session):
    """Test conversation creation."""
    customer_repo = CustomerRepository(db_session)
    customer = customer_repo.create(name="Test Customer", email="test@example.com")
    
    conv_repo = ConversationRepository(db_session)
    conv = conv_repo.create(
        session_id="session-123",
        customer_id=customer.id,
        channel="voice",
        status="active",
    )
    assert conv.id is not None
    assert conv.session_id == "session-123"
    assert conv.channel == "voice"


def test_conversation_repository_get_by_session_id(db_session: Session):
    """Test get conversation by session ID."""
    customer_repo = CustomerRepository(db_session)
    customer = customer_repo.create(name="Test Customer", email="test@example.com")
    
    conv_repo = ConversationRepository(db_session)
    conv = conv_repo.create(
        session_id="session-456",
        customer_id=customer.id,
        channel="sms",
    )
    
    found = conv_repo.get_by_session_id("session-456")
    assert found is not None
    assert found.id == conv.id


def test_conversation_repository_add_turn(db_session: Session):
    """Test add conversation turn."""
    customer_repo = CustomerRepository(db_session)
    customer = customer_repo.create(name="Test Customer", email="test@example.com")
    
    conv_repo = ConversationRepository(db_session)
    conv = conv_repo.create(
        session_id="session-789",
        customer_id=customer.id,
        channel="voice",
    )
    
    turn = conv_repo.add_turn(
        conversation_id=conv.id,
        turn_number=1,
        speaker="user",
        message="Hello, I need help",
        intent="greeting",
        confidence_score=0.95,
    )
    assert turn.id is not None
    assert turn.turn_number == 1
    assert turn.speaker == "user"


def test_conversation_repository_get_turns(db_session: Session):
    """Test get conversation turns."""
    customer_repo = CustomerRepository(db_session)
    customer = customer_repo.create(name="Test Customer", email="test@example.com")
    
    conv_repo = ConversationRepository(db_session)
    conv = conv_repo.create(
        session_id="session-999",
        customer_id=customer.id,
        channel="voice",
    )
    
    conv_repo.add_turn(conv.id, 1, "user", "Hello")
    conv_repo.add_turn(conv.id, 2, "agent", "Hi, how can I help?")
    conv_repo.add_turn(conv.id, 3, "user", "I need AC repair")
    
    turns = conv_repo.get_turns(conv.id)
    assert len(turns) == 3
    assert turns[0].turn_number == 1
    assert turns[2].turn_number == 3


# Transaction retry tests
def test_base_repository_retry_transaction(db_session: Session):
    """Test transaction retry logic."""
    repo = CustomerRepository(db_session)
    
    def create_customer():
        return repo.create(name="Test Customer", email="retry@example.com")
    
    customer = repo.retry_transaction(create_customer)
    assert customer.id is not None
    assert customer.name == "Test Customer"


# Update and delete tests
def test_base_repository_update(db_session: Session):
    """Test entity update."""
    repo = CustomerRepository(db_session)
    customer = repo.create(name="Old Name", email="test@example.com")
    
    updated = repo.update(customer.id, name="New Name", city="Boston")
    assert updated.name == "New Name"
    assert updated.city == "Boston"
    assert updated.email == "test@example.com"  # Unchanged


def test_base_repository_delete(db_session: Session):
    """Test entity deletion."""
    repo = CustomerRepository(db_session)
    customer = repo.create(name="Test Customer", email="test@example.com")
    
    deleted = repo.delete(customer.id)
    assert deleted is True
    
    found = repo.get(customer.id)
    assert found is None


def test_base_repository_get_all(db_session: Session):
    """Test get all entities with pagination."""
    repo = CustomerRepository(db_session)
    for i in range(15):
        repo.create(name=f"Customer {i}", email=f"customer{i}@example.com")
    
    # Get first page
    page1 = repo.get_all(skip=0, limit=10)
    assert len(page1) == 10
    
    # Get second page
    page2 = repo.get_all(skip=10, limit=10)
    assert len(page2) == 5
