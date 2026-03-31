"""
Unit Tests for Intake Agent Inventory Integration

Simple unit tests that don't require database setup.

Validates: Requirements 4.6, 4.7
"""

import pytest
from agents.intake import IntakeAgent, PartQuery
from llm.unified_client import UnifiedLLMClient


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


class TestCommonPartsForService:
    """Test getting common parts for service types."""
    
    @pytest.mark.asyncio
    async def test_get_common_parts_hvac(self, intake_agent):
        """Test getting common parts for HVAC service."""
        # Act
        parts = await intake_agent.get_common_parts_for_service("HVAC")
        
        # Assert
        assert len(parts) > 0
        assert all(isinstance(p, PartQuery) for p in parts)
        assert all(p.category == "HVAC" for p in parts)
        
        # Check for expected common HVAC parts
        part_names = [p.name.lower() for p in parts]
        assert any("thermostat" in name for name in part_names)
        assert any("capacitor" in name for name in part_names)
        assert any("filter" in name for name in part_names)
    
    @pytest.mark.asyncio
    async def test_get_common_parts_plumbing(self, intake_agent):
        """Test getting common parts for Plumbing service."""
        # Act
        parts = await intake_agent.get_common_parts_for_service("Plumbing")
        
        # Assert
        assert len(parts) > 0
        assert all(p.category == "Plumbing" for p in parts)
        
        # Check for expected common plumbing parts
        part_names = [p.name.lower() for p in parts]
        assert any("valve" in name for name in part_names)
        assert any("fitting" in name or "pipe" in name for name in part_names)
    
    @pytest.mark.asyncio
    async def test_get_common_parts_electrical(self, intake_agent):
        """Test getting common parts for Electrical service."""
        # Act
        parts = await intake_agent.get_common_parts_for_service("Electrical")
        
        # Assert
        assert len(parts) > 0
        assert all(p.category == "Electrical" for p in parts)
        
        # Check for expected common electrical parts
        part_names = [p.name.lower() for p in parts]
        assert any("breaker" in name for name in part_names)
        assert any("outlet" in name for name in part_names)
    
    @pytest.mark.asyncio
    async def test_get_common_parts_appliance(self, intake_agent):
        """Test getting common parts for Appliance service."""
        # Act
        parts = await intake_agent.get_common_parts_for_service("Appliance")
        
        # Assert
        assert len(parts) > 0
        assert all(p.category == "Appliance" for p in parts)
        
        # Check for expected common appliance parts
        part_names = [p.name.lower() for p in parts]
        assert any("element" in name or "heating" in name for name in part_names)
        assert any("motor" in name for name in part_names)
    
    @pytest.mark.asyncio
    async def test_get_common_parts_unknown_service(self, intake_agent):
        """Test getting common parts for unknown service type."""
        # Act
        parts = await intake_agent.get_common_parts_for_service("Unknown")
        
        # Assert
        assert len(parts) == 0  # No common parts for unknown service
    
    @pytest.mark.asyncio
    async def test_get_common_parts_general_service(self, intake_agent):
        """Test getting common parts for General service type."""
        # Act
        parts = await intake_agent.get_common_parts_for_service("General")
        
        # Assert
        assert len(parts) == 0  # No specific common parts for general service


class TestPartQueryModel:
    """Test PartQuery data model."""
    
    def test_part_query_with_part_number(self):
        """Test creating PartQuery with part number."""
        query = PartQuery(part_number="HVAC-001")
        
        assert query.part_number == "HVAC-001"
        assert query.name is None
        assert query.category is None
        assert query.service_type is None
    
    def test_part_query_with_name(self):
        """Test creating PartQuery with name."""
        query = PartQuery(name="Thermostat")
        
        assert query.part_number is None
        assert query.name == "Thermostat"
        assert query.category is None
        assert query.service_type is None
    
    def test_part_query_with_category(self):
        """Test creating PartQuery with category."""
        query = PartQuery(category="HVAC")
        
        assert query.part_number is None
        assert query.name is None
        assert query.category == "HVAC"
        assert query.service_type is None
    
    def test_part_query_with_all_fields(self):
        """Test creating PartQuery with all fields."""
        query = PartQuery(
            part_number="HVAC-001",
            name="Thermostat",
            category="HVAC",
            service_type="HVAC"
        )
        
        assert query.part_number == "HVAC-001"
        assert query.name == "Thermostat"
        assert query.category == "HVAC"
        assert query.service_type == "HVAC"


class TestIntakeAgentInventoryMethods:
    """Test that inventory methods exist and are callable."""
    
    def test_check_parts_availability_exists(self, intake_agent):
        """Test that check_parts_availability method exists."""
        assert hasattr(intake_agent, 'check_parts_availability')
        assert callable(intake_agent.check_parts_availability)
    
    def test_search_parts_exists(self, intake_agent):
        """Test that search_parts method exists."""
        assert hasattr(intake_agent, 'search_parts')
        assert callable(intake_agent.search_parts)
    
    def test_get_common_parts_for_service_exists(self, intake_agent):
        """Test that get_common_parts_for_service method exists."""
        assert hasattr(intake_agent, 'get_common_parts_for_service')
        assert callable(intake_agent.get_common_parts_for_service)
    
    def test_find_alternative_parts_exists(self, intake_agent):
        """Test that _find_alternative_parts method exists."""
        assert hasattr(intake_agent, '_find_alternative_parts')
        assert callable(intake_agent._find_alternative_parts)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
