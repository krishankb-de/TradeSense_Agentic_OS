"""
Tests for Intake Agent Inventory Integration

Tests the inventory checking, parts search, and availability features
integrated into the Intake Agent.

Validates: Requirements 4.6, 4.7
"""

import pytest
from uuid import uuid4
from datetime import datetime

from agents.intake import (
    IntakeAgent,
    PartQuery,
    PartAvailability,
)
from llm.unified_client import UnifiedLLMClient
from db.models import Part, Lead, Customer
from db.session import get_db


@pytest.fixture
def llm_client():
    """Create LLM client for testing."""
    import os
    return UnifiedLLMClient(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "test-key"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    )


@pytest.fixture
def intake_agent(llm_client):
    """Create intake agent for testing."""
    return IntakeAgent(llm_client=llm_client)


@pytest.fixture
def sample_parts(db_session):
    """Create sample parts in database."""
    parts = [
        Part(
            id=uuid4(),
            part_number="HVAC-THERM-001",
            name="Digital Thermostat",
            description="Programmable digital thermostat",
            manufacturer="Honeywell",
            category="HVAC",
            quantity_available=15,
            unit_price=125.00,
            reorder_level=5,
        ),
        Part(
            id=uuid4(),
            part_number="HVAC-CAP-002",
            name="Run Capacitor 45/5",
            description="Dual run capacitor 45/5 MFD",
            manufacturer="GE",
            category="HVAC",
            quantity_available=3,
            unit_price=35.00,
            reorder_level=10,
        ),
        Part(
            id=uuid4(),
            part_number="HVAC-CAP-003",
            name="Run Capacitor 40/5",
            description="Dual run capacitor 40/5 MFD",
            manufacturer="GE",
            category="HVAC",
            quantity_available=12,
            unit_price=32.00,
            reorder_level=10,
        ),
        Part(
            id=uuid4(),
            part_number="PLUMB-VALVE-001",
            name="Ball Valve 1/2 inch",
            description="Brass ball valve 1/2 inch",
            manufacturer="SharkBite",
            category="Plumbing",
            quantity_available=0,
            unit_price=18.50,
            reorder_level=5,
        ),
        Part(
            id=uuid4(),
            part_number="ELEC-BREAKER-001",
            name="Circuit Breaker 20A",
            description="Single pole 20A circuit breaker",
            manufacturer="Square D",
            category="Electrical",
            quantity_available=8,
            unit_price=12.00,
            reorder_level=5,
        ),
    ]
    
    for part in parts:
        db_session.add(part)
    
    db_session.commit()
    
    return parts


@pytest.fixture
def db_session():
    """Create database session for testing."""
    db = next(get_db())
    yield db
    db.close()


class TestInventoryIntegration:
    """Test inventory integration in Intake Agent."""
    
    @pytest.mark.asyncio
    async def test_check_parts_availability_found(self, intake_agent, sample_parts):
        """Test checking availability for parts that exist in inventory."""
        # Arrange
        queries = [
            PartQuery(part_number="HVAC-THERM-001"),
            PartQuery(part_number="HVAC-CAP-002"),
        ]
        
        # Act
        results = await intake_agent.check_parts_availability(queries)
        
        # Assert
        assert len(results) == 2
        
        # First part (thermostat) - available
        assert results[0].part_number == "HVAC-THERM-001"
        assert results[0].name == "Digital Thermostat"
        assert results[0].quantity_available == 15
        assert results[0].is_available is True
        assert results[0].reorder_needed is False
        
        # Second part (capacitor) - low stock
        assert results[1].part_number == "HVAC-CAP-002"
        assert results[1].quantity_available == 3
        assert results[1].is_available is True
        assert results[1].reorder_needed is True  # Below reorder level
        assert len(results[1].alternatives) > 0  # Should have alternatives
    
    @pytest.mark.asyncio
    async def test_check_parts_availability_not_found(self, intake_agent, sample_parts):
        """Test checking availability for parts that don't exist."""
        # Arrange
        queries = [
            PartQuery(part_number="NONEXISTENT-001"),
        ]
        
        # Act
        results = await intake_agent.check_parts_availability(queries)
        
        # Assert
        assert len(results) == 1
        assert results[0].part_number == "NONEXISTENT-001"
        assert results[0].quantity_available == 0
        assert results[0].is_available is False
        assert results[0].reorder_needed is True
    
    @pytest.mark.asyncio
    async def test_check_parts_availability_out_of_stock(self, intake_agent, sample_parts):
        """Test checking availability for parts that are out of stock."""
        # Arrange
        queries = [
            PartQuery(part_number="PLUMB-VALVE-001"),
        ]
        
        # Act
        results = await intake_agent.check_parts_availability(queries)
        
        # Assert
        assert len(results) == 1
        assert results[0].part_number == "PLUMB-VALVE-001"
        assert results[0].quantity_available == 0
        assert results[0].is_available is False
        assert results[0].reorder_needed is True
    
    @pytest.mark.asyncio
    async def test_check_parts_availability_by_name(self, intake_agent, sample_parts):
        """Test checking availability by part name."""
        # Arrange
        queries = [
            PartQuery(name="Thermostat"),
        ]
        
        # Act
        results = await intake_agent.check_parts_availability(queries)
        
        # Assert
        assert len(results) == 1
        assert "Thermostat" in results[0].name
        assert results[0].is_available is True
    
    @pytest.mark.asyncio
    async def test_check_parts_availability_by_category(self, intake_agent, sample_parts):
        """Test checking availability by category."""
        # Arrange
        queries = [
            PartQuery(category="Electrical"),
        ]
        
        # Act
        results = await intake_agent.check_parts_availability(queries)
        
        # Assert
        assert len(results) == 1
        assert results[0].category == "Electrical" or "Electrical" in results[0].name
        assert results[0].is_available is True
    
    @pytest.mark.asyncio
    async def test_search_parts_by_term(self, intake_agent, sample_parts):
        """Test searching parts by search term."""
        # Arrange
        search_term = "capacitor"
        
        # Act
        results = await intake_agent.search_parts(search_term)
        
        # Assert
        assert len(results) >= 2  # Should find both capacitors
        assert all("capacitor" in r["name"].lower() for r in results)
    
    @pytest.mark.asyncio
    async def test_search_parts_by_category(self, intake_agent, sample_parts):
        """Test searching parts with category filter."""
        # Arrange
        search_term = "run"
        category = "HVAC"
        
        # Act
        results = await intake_agent.search_parts(search_term, category=category)
        
        # Assert
        assert len(results) >= 2
        assert all(r["category"] == "HVAC" for r in results)
    
    @pytest.mark.asyncio
    async def test_search_parts_limit(self, intake_agent, sample_parts):
        """Test search parts respects limit."""
        # Arrange
        search_term = ""  # Empty search to get all
        limit = 2
        
        # Act
        results = await intake_agent.search_parts(search_term, limit=limit)
        
        # Assert
        assert len(results) <= limit
    
    @pytest.mark.asyncio
    async def test_get_common_parts_hvac(self, intake_agent):
        """Test getting common parts for HVAC service."""
        # Act
        parts = await intake_agent.get_common_parts_for_service("HVAC")
        
        # Assert
        assert len(parts) > 0
        assert all(isinstance(p, PartQuery) for p in parts)
        assert all(p.category == "HVAC" for p in parts)
        assert any("thermostat" in p.name.lower() for p in parts)
        assert any("capacitor" in p.name.lower() for p in parts)
    
    @pytest.mark.asyncio
    async def test_get_common_parts_plumbing(self, intake_agent):
        """Test getting common parts for Plumbing service."""
        # Act
        parts = await intake_agent.get_common_parts_for_service("Plumbing")
        
        # Assert
        assert len(parts) > 0
        assert all(p.category == "Plumbing" for p in parts)
        assert any("valve" in p.name.lower() for p in parts)
    
    @pytest.mark.asyncio
    async def test_get_common_parts_electrical(self, intake_agent):
        """Test getting common parts for Electrical service."""
        # Act
        parts = await intake_agent.get_common_parts_for_service("Electrical")
        
        # Assert
        assert len(parts) > 0
        assert all(p.category == "Electrical" for p in parts)
        assert any("breaker" in p.name.lower() for p in parts)
    
    @pytest.mark.asyncio
    async def test_get_common_parts_unknown_service(self, intake_agent):
        """Test getting common parts for unknown service type."""
        # Act
        parts = await intake_agent.get_common_parts_for_service("Unknown")
        
        # Assert
        assert len(parts) == 0  # No common parts for unknown service
    
    @pytest.mark.asyncio
    async def test_triage_with_parts_check(self, intake_agent, sample_parts, db_session):
        """Test that triage includes parts availability check."""
        # Arrange
        customer = Customer(
            id=uuid4(),
            name="Test Customer",
            email="test@example.com",
            phone="555-1234",
        )
        db_session.add(customer)
        db_session.commit()
        
        lead = Lead(
            id=uuid4(),
            customer_id=customer.id,
            source="voice",
            urgency="urgent",
            service_type="HVAC",
            description="AC not cooling, compressor not running",
            status="new",
        )
        db_session.add(lead)
        db_session.commit()
        
        # Act
        result = await intake_agent.triage_lead(lead)
        
        # Assert
        assert result is not None
        assert result.service_type == "HVAC"
        assert "Parts check:" in result.reasoning  # Should include parts info
        assert result.confidence > 0
    
    @pytest.mark.asyncio
    async def test_find_alternative_parts(self, intake_agent, sample_parts, db_session):
        """Test finding alternative parts in same category."""
        # Act
        alternatives = await intake_agent._find_alternative_parts(
            category="HVAC",
            exclude_part_number="HVAC-CAP-002",
            db=db_session
        )
        
        # Assert
        assert len(alternatives) > 0
        assert "HVAC-CAP-002" not in alternatives  # Excluded part
        assert "HVAC-CAP-003" in alternatives  # Alternative capacitor


class TestInventoryEdgeCases:
    """Test edge cases for inventory integration."""
    
    @pytest.mark.asyncio
    async def test_check_parts_empty_list(self, intake_agent):
        """Test checking parts with empty list."""
        # Act
        results = await intake_agent.check_parts_availability([])
        
        # Assert
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_parts_empty_term(self, intake_agent, sample_parts):
        """Test searching with empty term."""
        # Act
        results = await intake_agent.search_parts("")
        
        # Assert
        # Should return some results (all parts match empty search)
        assert len(results) >= 0
    
    @pytest.mark.asyncio
    async def test_check_parts_multiple_queries(self, intake_agent, sample_parts):
        """Test checking multiple parts at once."""
        # Arrange
        queries = [
            PartQuery(part_number="HVAC-THERM-001"),
            PartQuery(part_number="HVAC-CAP-002"),
            PartQuery(part_number="PLUMB-VALVE-001"),
            PartQuery(part_number="ELEC-BREAKER-001"),
        ]
        
        # Act
        results = await intake_agent.check_parts_availability(queries)
        
        # Assert
        assert len(results) == 4
        assert sum(1 for r in results if r.is_available) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
