"""
Unit Tests for KiCost Distributor Scraping Integration

Tests BOM pricing, distributor comparison, and best price selection.

**Validates: Requirements 7.5, 7.6, 7.7, 15.2, 15.3**
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from datetime import datetime

from integrations.kicost import (
    KiCostClient,
    DistributorConfig,
    DistributorPrice,
    PriceBreak,
    BOMItem,
    BOMPricing,
)


@pytest.fixture
def distributor_configs():
    """Create test distributor configurations"""
    return [
        DistributorConfig(name="digikey", enabled=True, priority=10),
        DistributorConfig(name="mouser", enabled=True, priority=8),
        DistributorConfig(name="arrow", enabled=True, priority=5),
        DistributorConfig(name="newark", enabled=True, priority=3),
        DistributorConfig(name="tme", enabled=True, priority=1),
    ]


@pytest.fixture
def kicost_client(distributor_configs):
    """Create KiCost client"""
    return KiCostClient(distributor_configs)


@pytest.fixture
def sample_price_breaks():
    """Create sample price breaks"""
    return [
        PriceBreak(quantity=1, price=Decimal("1.50")),
        PriceBreak(quantity=10, price=Decimal("1.20")),
        PriceBreak(quantity=100, price=Decimal("0.90")),
        PriceBreak(quantity=1000, price=Decimal("0.75")),
    ]


# ============================================================================
# Price Scraping Tests
# **Validates: Requirement 7.5**
# ============================================================================

class TestPriceScraping:
    """Test distributor price scraping"""
    
    @pytest.mark.asyncio
    async def test_get_part_prices_from_multiple_distributors(self, kicost_client):
        """Test getting prices from all enabled distributors"""
        # Mock scraping methods
        kicost_client._scrape_digikey = AsyncMock(return_value=DistributorPrice(
            distributor="digikey",
            part_number="DK-12345",
            mpn="ATMEGA328P-PU",
            stock=1000,
            price_breaks=[PriceBreak(quantity=1, price=Decimal("2.50"))],
        ))
        kicost_client._scrape_mouser = AsyncMock(return_value=DistributorPrice(
            distributor="mouser",
            part_number="MS-67890",
            mpn="ATMEGA328P-PU",
            stock=500,
            price_breaks=[PriceBreak(quantity=1, price=Decimal("2.45"))],
        ))
        kicost_client._scrape_arrow = AsyncMock(return_value=None)
        kicost_client._scrape_newark = AsyncMock(return_value=None)
        kicost_client._scrape_tme = AsyncMock(return_value=None)
        
        prices = await kicost_client.get_part_prices("ATMEGA328P-PU", "Microchip", 1)
        
        assert len(prices) == 2
        assert prices[0].distributor == "digikey"
        assert prices[1].distributor == "mouser"
    
    @pytest.mark.asyncio
    async def test_handle_distributor_scraping_failure(self, kicost_client):
        """Test handling when distributor scraping fails"""
        kicost_client._scrape_digikey = AsyncMock(
            side_effect=Exception("Scraping failed")
        )
        kicost_client._scrape_mouser = AsyncMock(return_value=DistributorPrice(
            distributor="mouser",
            part_number="MS-67890",
            mpn="TEST-PART",
            stock=100,
            price_breaks=[PriceBreak(quantity=1, price=Decimal("1.00"))],
        ))
        kicost_client._scrape_arrow = AsyncMock(return_value=None)
        kicost_client._scrape_newark = AsyncMock(return_value=None)
        kicost_client._scrape_tme = AsyncMock(return_value=None)
        
        prices = await kicost_client.get_part_prices("TEST-PART")
        
        # Should continue with other distributors despite failure
        assert len(prices) == 1
        assert prices[0].distributor == "mouser"


# ============================================================================
# BOM Pricing Tests
# **Validates: Requirement 7.5**
# ============================================================================

class TestBOMPricing:
    """Test BOM pricing functionality"""
    
    @pytest.mark.asyncio
    async def test_price_bom(self, kicost_client):
        """Test pricing entire BOM"""
        bom = [
            BOMItem(
                reference="R1",
                quantity=10,
                mpn="RC0805FR-0710KL",
                manufacturer="Yageo",
                description="10K resistor",
            ),
            BOMItem(
                reference="C1",
                quantity=5,
                mpn="CL21B104KBCNNNC",
                manufacturer="Samsung",
                description="100nF capacitor",
            ),
        ]
        
        # Mock price retrieval
        kicost_client.get_part_prices = AsyncMock(side_effect=[
            [DistributorPrice(
                distributor="digikey",
                part_number="DK-R1",
                mpn="RC0805FR-0710KL",
                stock=10000,
                price_breaks=[PriceBreak(quantity=1, price=Decimal("0.10"))],
            )],
            [DistributorPrice(
                distributor="mouser",
                part_number="MS-C1",
                mpn="CL21B104KBCNNNC",
                stock=5000,
                price_breaks=[PriceBreak(quantity=1, price=Decimal("0.15"))],
            )],
        ])
        
        results = await kicost_client.price_bom(bom)
        
        assert len(results) == 2
        assert results[0].item.reference == "R1"
        assert results[0].best_price is not None
        assert results[0].total_cost == Decimal("1.00")  # 10 * 0.10
        assert results[1].item.reference == "C1"
        assert results[1].total_cost == Decimal("0.75")  # 5 * 0.15
    
    @pytest.mark.asyncio
    async def test_skip_bom_items_without_mpn(self, kicost_client):
        """Test skipping BOM items without MPN"""
        bom = [
            BOMItem(
                reference="R1",
                quantity=10,
                mpn=None,  # No MPN
                description="Generic resistor",
            ),
        ]
        
        results = await kicost_client.price_bom(bom)
        
        assert len(results) == 0


# ============================================================================
# Price Comparison Tests
# **Validates: Requirement 7.6**
# ============================================================================

class TestPriceComparison:
    """Test price comparison across distributors"""
    
    def test_compare_prices(self, kicost_client, sample_price_breaks):
        """Test comparing prices from multiple distributors"""
        prices = [
            DistributorPrice(
                distributor="digikey",
                part_number="DK-123",
                mpn="TEST-PART",
                stock=1000,
                moq=1,
                price_breaks=sample_price_breaks,
                lead_time_days=1,
            ),
            DistributorPrice(
                distributor="mouser",
                part_number="MS-456",
                mpn="TEST-PART",
                stock=500,
                moq=1,
                price_breaks=[
                    PriceBreak(quantity=1, price=Decimal("1.45")),
                    PriceBreak(quantity=10, price=Decimal("1.15")),
                ],
                lead_time_days=2,
            ),
        ]
        
        comparison = kicost_client.compare_prices(prices, quantity=10)
        
        assert len(comparison) == 2
        # Should be sorted by total price
        assert comparison[0]["distributor"] == "mouser"  # 10 * 1.15 = 11.50
        assert comparison[1]["distributor"] == "digikey"  # 10 * 1.20 = 12.00
        assert comparison[0]["total_price"] == 11.50
        assert comparison[1]["total_price"] == 12.00
    
    def test_get_price_for_quantity(self, kicost_client, sample_price_breaks):
        """Test getting unit price for specific quantity"""
        price = DistributorPrice(
            distributor="digikey",
            part_number="DK-123",
            mpn="TEST-PART",
            stock=1000,
            price_breaks=sample_price_breaks,
        )
        
        # Test different quantities
        assert kicost_client.get_price_for_quantity(price, 1) == Decimal("1.50")
        assert kicost_client.get_price_for_quantity(price, 10) == Decimal("1.20")
        assert kicost_client.get_price_for_quantity(price, 50) == Decimal("1.20")
        assert kicost_client.get_price_for_quantity(price, 100) == Decimal("0.90")
        assert kicost_client.get_price_for_quantity(price, 1000) == Decimal("0.75")


# ============================================================================
# Best Price Selection Tests
# **Validates: Requirement 7.7**
# ============================================================================

class TestBestPriceSelection:
    """Test best price selection logic"""
    
    def test_select_best_price_by_total_cost(self, kicost_client):
        """Test selecting best price based on total cost"""
        prices = [
            DistributorPrice(
                distributor="digikey",
                part_number="DK-123",
                mpn="TEST-PART",
                stock=1000,
                price_breaks=[PriceBreak(quantity=1, price=Decimal("1.50"))],
            ),
            DistributorPrice(
                distributor="mouser",
                part_number="MS-456",
                mpn="TEST-PART",
                stock=500,
                price_breaks=[PriceBreak(quantity=1, price=Decimal("1.30"))],
            ),
        ]
        
        best = kicost_client.select_best_price(prices, quantity=10)
        
        assert best is not None
        assert best.distributor == "mouser"  # Lower price
    
    def test_select_best_price_prefers_in_stock(self, kicost_client):
        """Test that in-stock items are preferred"""
        prices = [
            DistributorPrice(
                distributor="digikey",
                part_number="DK-123",
                mpn="TEST-PART",
                stock=5,  # Insufficient stock
                price_breaks=[PriceBreak(quantity=1, price=Decimal("1.00"))],
            ),
            DistributorPrice(
                distributor="mouser",
                part_number="MS-456",
                mpn="TEST-PART",
                stock=100,  # Sufficient stock
                price_breaks=[PriceBreak(quantity=1, price=Decimal("1.10"))],
            ),
        ]
        
        best = kicost_client.select_best_price(prices, quantity=10)
        
        assert best is not None
        assert best.distributor == "mouser"  # Has stock
    
    def test_select_best_price_considers_priority(self, kicost_client):
        """Test that distributor priority is considered"""
        prices = [
            DistributorPrice(
                distributor="digikey",  # Priority 10
                part_number="DK-123",
                mpn="TEST-PART",
                stock=100,
                price_breaks=[PriceBreak(quantity=1, price=Decimal("1.00"))],
            ),
            DistributorPrice(
                distributor="mouser",  # Priority 8
                part_number="MS-456",
                mpn="TEST-PART",
                stock=100,
                price_breaks=[PriceBreak(quantity=1, price=Decimal("1.00"))],
            ),
        ]
        
        best = kicost_client.select_best_price(prices, quantity=10)
        
        assert best is not None
        # When prices are equal, higher priority wins
        assert best.distributor == "digikey"
    
    def test_select_best_price_handles_empty_list(self, kicost_client):
        """Test handling empty price list"""
        best = kicost_client.select_best_price([], quantity=10)
        
        assert best is None


# ============================================================================
# BOM Summary Tests
# ============================================================================

class TestBOMSummary:
    """Test BOM summary calculations"""
    
    def test_calculate_bom_total(self, kicost_client):
        """Test calculating total BOM cost"""
        bom_pricing = [
            BOMPricing(
                item=BOMItem(reference="R1", quantity=10, mpn="R1-MPN"),
                total_cost=Decimal("10.00"),
            ),
            BOMPricing(
                item=BOMItem(reference="C1", quantity=5, mpn="C1-MPN"),
                total_cost=Decimal("7.50"),
            ),
            BOMPricing(
                item=BOMItem(reference="U1", quantity=1, mpn="U1-MPN"),
                total_cost=None,  # Not priced
            ),
        ]
        
        total = kicost_client.calculate_bom_total(bom_pricing)
        
        assert total == Decimal("17.50")
    
    def test_get_bom_summary(self, kicost_client):
        """Test getting BOM summary"""
        bom_pricing = [
            BOMPricing(
                item=BOMItem(reference="R1", quantity=10, mpn="R1-MPN"),
                best_price=DistributorPrice(
                    distributor="digikey",
                    part_number="DK-R1",
                    mpn="R1-MPN",
                    stock=100,
                    price_breaks=[],
                ),
                total_cost=Decimal("10.00"),
            ),
            BOMPricing(
                item=BOMItem(reference="C1", quantity=5, mpn="C1-MPN"),
                best_price=DistributorPrice(
                    distributor="mouser",
                    part_number="MS-C1",
                    mpn="C1-MPN",
                    stock=2,  # Insufficient
                    price_breaks=[],
                ),
                total_cost=Decimal("7.50"),
            ),
        ]
        
        summary = kicost_client.get_bom_summary(bom_pricing)
        
        assert summary["total_items"] == 2
        assert summary["total_cost"] == 17.50
        assert summary["in_stock"] == 1
        assert summary["out_of_stock"] == 1
        assert summary["distributor_breakdown"]["digikey"] == 1
        assert summary["distributor_breakdown"]["mouser"] == 1


# ============================================================================
# Error Handling Tests
# **Validates: Requirement 15.3**
# ============================================================================

class TestErrorHandling:
    """Test error handling and resilience"""
    
    @pytest.mark.asyncio
    async def test_handle_scraping_errors_gracefully(self, kicost_client):
        """Test that scraping errors don't crash the system"""
        kicost_client._scrape_digikey = AsyncMock(
            side_effect=Exception("Network error")
        )
        kicost_client._scrape_mouser = AsyncMock(
            side_effect=Exception("API rate limit")
        )
        kicost_client._scrape_arrow = AsyncMock(return_value=None)
        kicost_client._scrape_newark = AsyncMock(return_value=None)
        kicost_client._scrape_tme = AsyncMock(return_value=None)
        
        prices = await kicost_client.get_part_prices("TEST-PART")
        
        # Should return empty list, not crash
        assert prices == []
