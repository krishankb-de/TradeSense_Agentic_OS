"""
Unit Tests for Part-DB API Integration

Tests component search, KiCad integration, and alternative part suggestions.

**Validates: Requirements 7.3, 7.4, 15.2, 15.3**
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

from integrations.partdb import (
    PartDBClient,
    PartDBConfig,
    ComponentSpec,
    KiCadSymbol,
    KiCadFootprint,
)


@pytest.fixture
def partdb_config():
    """Create test Part-DB configuration"""
    return PartDBConfig(
        base_url="https://partdb.example.com",
        api_token="test-token-456",
        timeout=30,
        verify_ssl=True,
    )


@pytest.fixture
async def partdb_client(partdb_config):
    """Create Part-DB client with mocked HTTP client"""
    client = PartDBClient(partdb_config)
    client.client = AsyncMock()
    
    yield client
    
    await client.close()


# ============================================================================
# Component Search Tests
# **Validates: Requirement 7.3**
# ============================================================================

class TestComponentSearch:
    """Test component search and retrieval"""
    
    @pytest.mark.asyncio
    async def test_search_components_by_name(self, partdb_client):
        """Test searching components by name"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "ATmega328P",
                    "description": "8-bit AVR microcontroller",
                    "category": "Microcontrollers",
                    "manufacturer": "Microchip",
                    "mpn": "ATMEGA328P-PU",
                    "footprint": "DIP-28",
                    "symbol": "MCU_Microchip_ATmega:ATmega328P",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        components = await partdb_client.search_components(search="ATmega328")
        
        assert len(components) == 1
        assert components[0].name == "ATmega328P"
        assert components[0].manufacturer == "Microchip"
        assert components[0].mpn == "ATMEGA328P-PU"
    
    @pytest.mark.asyncio
    async def test_search_components_with_filters(self, partdb_client):
        """Test searching with category and manufacturer filters"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        await partdb_client.search_components(
            search="resistor",
            category="Resistors",
            manufacturer="Yageo",
            limit=50,
        )
        
        call_args = partdb_client.client.get.call_args
        assert call_args[0][0] == "/api/parts"
        params = call_args[1]["params"]
        assert params["search"] == "resistor"
        assert params["category"] == "Resistors"
        assert params["manufacturer"] == "Yageo"
    
    @pytest.mark.asyncio
    async def test_get_component_by_id(self, partdb_client):
        """Test retrieving component by ID"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 42,
            "name": "Capacitor 100nF",
            "description": "Ceramic capacitor",
            "category": "Capacitors",
            "value": "100nF",
            "package": "0805",
        }
        mock_response.raise_for_status = MagicMock()
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        component = await partdb_client.get_component(42)
        
        assert component.id == 42
        assert component.name == "Capacitor 100nF"
        assert component.value == "100nF"
    
    @pytest.mark.asyncio
    async def test_get_component_by_mpn(self, partdb_client):
        """Test retrieving component by manufacturer part number"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": 10,
                    "name": "LM358",
                    "mpn": "LM358N",
                    "manufacturer": "Texas Instruments",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        component = await partdb_client.get_component_by_mpn("LM358N")
        
        assert component is not None
        assert component.mpn == "LM358N"
    
    @pytest.mark.asyncio
    async def test_get_component_parameters(self, partdb_client):
        """Test retrieving component parameters"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": 1,
            "name": "Resistor 10K",
            "parameters": {
                "resistance": "10000",
                "tolerance": "1%",
                "power": "0.25W",
                "temperature_coefficient": "100ppm/°C",
            },
        }
        mock_response.raise_for_status = MagicMock()
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        params = await partdb_client.get_component_parameters(1)
        
        assert params["resistance"] == "10000"
        assert params["tolerance"] == "1%"
        assert params["power"] == "0.25W"


# ============================================================================
# KiCad Integration Tests
# **Validates: Requirement 7.4**
# ============================================================================

class TestKiCadIntegration:
    """Test KiCad symbol and footprint retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_kicad_symbol(self, partdb_client):
        """Test retrieving KiCad symbol for component"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "ATmega328P",
            "library": "MCU_Microchip_ATmega",
            "description": "8-bit AVR microcontroller",
            "keywords": ["AVR", "microcontroller", "8-bit"],
            "datasheet": "http://example.com/datasheet.pdf",
            "pins": [
                {"number": "1", "name": "PD0", "type": "bidirectional"},
                {"number": "2", "name": "PD1", "type": "bidirectional"},
            ],
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        symbol = await partdb_client.get_kicad_symbol(1)
        
        assert symbol is not None
        assert symbol.name == "ATmega328P"
        assert symbol.library == "MCU_Microchip_ATmega"
        assert len(symbol.pins) == 2
    
    @pytest.mark.asyncio
    async def test_get_kicad_symbol_not_found(self, partdb_client):
        """Test handling missing KiCad symbol"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        symbol = await partdb_client.get_kicad_symbol(999)
        
        assert symbol is None
    
    @pytest.mark.asyncio
    async def test_get_kicad_footprint(self, partdb_client):
        """Test retrieving KiCad footprint for component"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "DIP-28_W7.62mm",
            "library": "Package_DIP",
            "description": "28-lead DIP package",
            "tags": ["DIP", "THT"],
            "pads": [
                {"number": "1", "type": "thru_hole", "shape": "rect"},
                {"number": "2", "type": "thru_hole", "shape": "oval"},
            ],
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        footprint = await partdb_client.get_kicad_footprint(1)
        
        assert footprint is not None
        assert footprint.name == "DIP-28_W7.62mm"
        assert footprint.library == "Package_DIP"
        assert len(footprint.pads) == 2
    
    @pytest.mark.asyncio
    async def test_search_kicad_symbols(self, partdb_client):
        """Test searching for KiCad symbols"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "name": "R",
                    "library": "Device",
                    "description": "Resistor",
                    "keywords": ["R", "resistor"],
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        symbols = await partdb_client.search_kicad_symbols("resistor")
        
        assert len(symbols) == 1
        assert symbols[0].name == "R"
        assert symbols[0].library == "Device"
    
    @pytest.mark.asyncio
    async def test_search_kicad_footprints(self, partdb_client):
        """Test searching for KiCad footprints"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "name": "R_0805_2012Metric",
                    "library": "Resistor_SMD",
                    "description": "0805 resistor footprint",
                    "tags": ["resistor", "0805", "SMD"],
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        footprints = await partdb_client.search_kicad_footprints("0805")
        
        assert len(footprints) == 1
        assert footprints[0].name == "R_0805_2012Metric"


# ============================================================================
# Alternative Components Tests
# **Validates: Requirement 7.3**
# ============================================================================

class TestAlternativeComponents:
    """Test finding alternative/compatible components"""
    
    @pytest.mark.asyncio
    async def test_find_alternative_components(self, partdb_client):
        """Test finding alternative components"""
        # Mock original component
        original_response = MagicMock()
        original_response.json.return_value = {
            "id": 1,
            "name": "Resistor 10K",
            "category": "Resistors",
            "parameters": {
                "resistance": "10000",
                "tolerance": "1%",
                "power": "0.25W",
            },
        }
        original_response.raise_for_status = MagicMock()
        
        # Mock alternatives search
        alternatives_response = MagicMock()
        alternatives_response.json.return_value = {
            "data": [
                {
                    "id": 1,
                    "name": "Resistor 10K",
                    "category": "Resistors",
                    "parameters": {"resistance": "10000"},
                },
                {
                    "id": 2,
                    "name": "Resistor 10K Alt",
                    "category": "Resistors",
                    "parameters": {"resistance": "10000"},
                },
            ]
        }
        alternatives_response.raise_for_status = MagicMock()
        
        partdb_client.client.get = AsyncMock(
            side_effect=[original_response, alternatives_response]
        )
        
        alternatives = await partdb_client.find_alternative_components(1)
        
        assert len(alternatives) == 1  # Excludes original
        assert alternatives[0].id == 2


# ============================================================================
# Error Handling Tests
# **Validates: Requirement 15.3**
# ============================================================================

class TestErrorHandling:
    """Test error handling and retry logic"""
    
    @pytest.mark.asyncio
    async def test_handle_http_error(self, partdb_client):
        """Test handling HTTP errors"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 500 Server Error")
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(Exception, match="HTTP 500 Server Error"):
            await partdb_client.get_component(1)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, partdb_client):
        """Test successful health check"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        partdb_client.client.get = AsyncMock(return_value=mock_response)
        
        healthy = await partdb_client.health_check()
        
        assert healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, partdb_client):
        """Test failed health check"""
        partdb_client.client.get = AsyncMock(
            side_effect=Exception("Connection timeout")
        )
        
        healthy = await partdb_client.health_check()
        
        assert healthy is False
