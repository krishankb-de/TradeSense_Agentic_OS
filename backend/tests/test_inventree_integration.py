"""
Unit Tests for InvenTree API Integration

Tests inventory queries, part searches, and stock management.

**Validates: Requirements 7.1, 7.2, 7.9, 15.2, 15.3**
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

from integrations.inventree import (
    InvenTreeClient,
    InvenTreeConfig,
    PartInfo,
    StockItem,
    StockLocation,
)


@pytest.fixture
def inventree_config():
    """Create test InvenTree configuration"""
    return InvenTreeConfig(
        base_url="https://inventree.example.com",
        api_token="test-token-123",
        timeout=30,
        verify_ssl=True,
    )


@pytest.fixture
async def inventree_client(inventree_config):
    """Create InvenTree client with mocked HTTP client"""
    client = InvenTreeClient(inventree_config)
    
    # Mock the HTTP client
    client.client = AsyncMock()
    
    yield client
    
    await client.close()


# ============================================================================
# Part Operations Tests
# **Validates: Requirement 7.1**
# ============================================================================

class TestPartOperations:
    """Test part search and retrieval operations"""
    
    @pytest.mark.asyncio
    async def test_search_parts_success(self, inventree_client):
        """Test successful part search"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "pk": 1,
                    "name": "Resistor 10K",
                    "description": "10K Ohm resistor",
                    "category": "Resistors",
                    "in_stock": 100,
                    "available": 80,
                    "active": True,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        parts = await inventree_client.search_parts(search="10K")
        
        assert len(parts) == 1
        assert parts[0].name == "Resistor 10K"
        assert parts[0].in_stock == 100
        assert parts[0].available == 80
        
        inventree_client.client.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_parts_with_filters(self, inventree_client):
        """Test part search with category filter"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        await inventree_client.search_parts(
            search="capacitor",
            category=5,
            active=True,
            limit=50,
        )
        
        call_args = inventree_client.client.get.call_args
        assert call_args[0][0] == "/api/part/"
        assert call_args[1]["params"]["search"] == "capacitor"
        assert call_args[1]["params"]["category"] == 5
        assert call_args[1]["params"]["limit"] == 50
    
    @pytest.mark.asyncio
    async def test_get_part_by_id(self, inventree_client):
        """Test retrieving part by ID"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pk": 42,
            "name": "Capacitor 100uF",
            "description": "Electrolytic capacitor",
            "in_stock": 50,
            "available": 45,
            "active": True,
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        part = await inventree_client.get_part(42)
        
        assert part.pk == 42
        assert part.name == "Capacitor 100uF"
        assert part.in_stock == 50
        
        inventree_client.client.get.assert_called_once_with("/api/part/42/")
    
    @pytest.mark.asyncio
    async def test_get_part_by_ipn(self, inventree_client):
        """Test retrieving part by internal part number"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "pk": 10,
                    "name": "Custom Part",
                    "ipn": "IPN-12345",
                    "in_stock": 25,
                    "available": 25,
                    "active": True,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        part = await inventree_client.get_part_by_ipn("IPN-12345")
        
        assert part is not None
        assert part.pk == 10
        assert part.ipn == "IPN-12345"


# ============================================================================
# Stock Level Tests
# **Validates: Requirement 7.2, 7.9**
# ============================================================================

class TestStockOperations:
    """Test stock level queries and updates"""
    
    @pytest.mark.asyncio
    async def test_get_part_stock_level(self, inventree_client):
        """Test retrieving stock levels for a part"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pk": 1,
            "name": "Test Part",
            "in_stock": 100,
            "available": 80,
            "on_order": 50,
            "minimum_stock": 20,
            "active": True,
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        stock = await inventree_client.get_part_stock_level(1)
        
        assert stock["in_stock"] == 100
        assert stock["available"] == 80
        assert stock["on_order"] == 50
        assert stock["minimum_stock"] == 20
    
    @pytest.mark.asyncio
    async def test_check_part_availability_sufficient(self, inventree_client):
        """Test checking part availability when sufficient stock exists"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pk": 1,
            "name": "Test Part",
            "in_stock": 100,
            "available": 80,
            "on_order": 0,
            "minimum_stock": 10,
            "active": True,
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        available = await inventree_client.check_part_availability(1, 50)
        
        assert available is True
    
    @pytest.mark.asyncio
    async def test_check_part_availability_insufficient(self, inventree_client):
        """Test checking part availability when stock is insufficient"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pk": 1,
            "name": "Test Part",
            "in_stock": 100,
            "available": 30,
            "on_order": 0,
            "minimum_stock": 10,
            "active": True,
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        available = await inventree_client.check_part_availability(1, 50)
        
        assert available is False
    
    @pytest.mark.asyncio
    async def test_get_stock_items(self, inventree_client):
        """Test retrieving stock items"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "pk": 1,
                    "part": 10,
                    "part_name": "Test Part",
                    "location": 5,
                    "location_name": "Warehouse A",
                    "quantity": 50.0,
                    "status": 10,
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        items = await inventree_client.get_stock_items(part_id=10)
        
        assert len(items) == 1
        assert items[0].part == 10
        assert items[0].quantity == 50.0
    
    @pytest.mark.asyncio
    async def test_update_stock_quantity(self, inventree_client):
        """Test updating stock item quantity"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pk": 1,
            "part": 10,
            "quantity": 75.0,
            "notes": "Updated quantity",
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.patch = AsyncMock(return_value=mock_response)
        
        item = await inventree_client.update_stock_quantity(
            1, 75.0, notes="Updated quantity"
        )
        
        assert item.quantity == 75.0
        assert item.notes == "Updated quantity"
    
    @pytest.mark.asyncio
    async def test_add_stock(self, inventree_client):
        """Test adding stock for a part"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "pk": 2,
            "part": 10,
            "quantity": 100.0,
            "location": 5,
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.post = AsyncMock(return_value=mock_response)
        
        item = await inventree_client.add_stock(10, 100.0, location=5)
        
        assert item.part == 10
        assert item.quantity == 100.0
        assert item.location == 5


# ============================================================================
# Low Stock Alerts Tests
# **Validates: Requirement 7.9**
# ============================================================================

class TestLowStockAlerts:
    """Test low stock detection and alerts"""
    
    @pytest.mark.asyncio
    async def test_get_low_stock_parts(self, inventree_client):
        """Test retrieving parts with low stock"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "pk": 1,
                    "name": "Low Stock Part",
                    "in_stock": 5,
                    "minimum_stock": 20,
                    "available": 5,
                    "active": True,
                },
                {
                    "pk": 2,
                    "name": "Normal Stock Part",
                    "in_stock": 100,
                    "minimum_stock": 20,
                    "available": 100,
                    "active": True,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        low_stock = await inventree_client.get_low_stock_parts()
        
        assert len(low_stock) == 1
        assert low_stock[0].name == "Low Stock Part"
        assert low_stock[0].in_stock < low_stock[0].minimum_stock
    
    @pytest.mark.asyncio
    async def test_get_low_stock_parts_with_threshold(self, inventree_client):
        """Test retrieving parts below custom threshold"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "pk": 1,
                    "name": "Part A",
                    "in_stock": 15,
                    "minimum_stock": 10,
                    "available": 15,
                    "active": True,
                },
                {
                    "pk": 2,
                    "name": "Part B",
                    "in_stock": 5,
                    "minimum_stock": 10,
                    "available": 5,
                    "active": True,
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        low_stock = await inventree_client.get_low_stock_parts(threshold=10)
        
        assert len(low_stock) == 1
        assert low_stock[0].name == "Part B"


# ============================================================================
# Error Handling and Retry Tests
# **Validates: Requirement 15.3**
# ============================================================================

class TestErrorHandling:
    """Test error handling and retry logic"""
    
    @pytest.mark.asyncio
    async def test_handle_http_error(self, inventree_client):
        """Test handling HTTP errors"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP 404 Not Found")
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        with pytest.raises(Exception, match="HTTP 404 Not Found"):
            await inventree_client.get_part(999)
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, inventree_client):
        """Test successful health check"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        inventree_client.client.get = AsyncMock(return_value=mock_response)
        
        healthy = await inventree_client.health_check()
        
        assert healthy is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, inventree_client):
        """Test failed health check"""
        inventree_client.client.get = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        
        healthy = await inventree_client.health_check()
        
        assert healthy is False


# ============================================================================
# Connection Management Tests
# **Validates: Requirement 10.9**
# ============================================================================

class TestConnectionManagement:
    """Test connection lifecycle management"""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, inventree_config):
        """Test client initialization with config"""
        client = InvenTreeClient(inventree_config)
        
        assert client.config.base_url == "https://inventree.example.com"
        assert client.config.api_token == "test-token-123"
        assert client.config.timeout == 30
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, inventree_config):
        """Test using client as async context manager"""
        async with InvenTreeClient(inventree_config) as client:
            assert client is not None
            assert client.config.base_url == "https://inventree.example.com"
