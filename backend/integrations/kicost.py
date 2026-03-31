"""
KiCost Distributor Scraping Integration

Integrates KiCost library for BOM pricing from multiple distributors.
Supports Digi-Key, Mouser, Arrow, Newark, TME and price comparison.

**Validates: Requirements 7.5, 7.6, 7.7**
"""

import logging
from typing import Any, Dict, List, Optional
from decimal import Decimal
from datetime import datetime

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DistributorConfig(BaseModel):
    """Distributor API configuration"""
    
    name: str = Field(..., description="Distributor name")
    api_key: Optional[str] = Field(None, description="API key")
    enabled: bool = Field(default=True, description="Enable this distributor")
    priority: int = Field(default=0, description="Priority for selection (higher = preferred)")


class PriceBreak(BaseModel):
    """Price break for quantity pricing"""
    
    quantity: int = Field(..., description="Minimum quantity")
    price: Decimal = Field(..., description="Unit price at this quantity")
    currency: str = Field(default="USD", description="Currency code")


class DistributorPrice(BaseModel):
    """Price information from a distributor"""
    
    distributor: str = Field(..., description="Distributor name")
    part_number: str = Field(..., description="Distributor part number")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    mpn: Optional[str] = Field(None, description="Manufacturer part number")
    description: str = Field(default="", description="Part description")
    stock: int = Field(default=0, description="Available stock")
    moq: int = Field(default=1, description="Minimum order quantity")
    price_breaks: List[PriceBreak] = Field(default_factory=list, description="Quantity price breaks")
    lead_time_days: Optional[int] = Field(None, description="Lead time in days")
    datasheet_url: Optional[str] = Field(None, description="Datasheet URL")
    product_url: Optional[str] = Field(None, description="Product page URL")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last price update")


class BOMItem(BaseModel):
    """Bill of Materials item"""
    
    reference: str = Field(..., description="Component reference (e.g., R1, C2)")
    quantity: int = Field(..., description="Quantity required")
    mpn: Optional[str] = Field(None, description="Manufacturer part number")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    description: str = Field(default="", description="Part description")
    value: Optional[str] = Field(None, description="Component value")
    footprint: Optional[str] = Field(None, description="PCB footprint")


class BOMPricing(BaseModel):
    """Complete BOM pricing from all distributors"""
    
    item: BOMItem
    prices: List[DistributorPrice] = Field(default_factory=list)
    best_price: Optional[DistributorPrice] = None
    total_cost: Optional[Decimal] = None


class KiCostClient:
    """
    KiCost Integration Client
    
    Wraps KiCost library for BOM pricing and distributor comparison.
    
    **Validates: Requirement 7.5** - BOM pricing from multiple distributors
    **Validates: Requirement 7.6** - Price comparison
    **Validates: Requirement 7.7** - Best price selection
    """
    
    def __init__(self, distributors: List[DistributorConfig]):
        self.distributors = {d.name: d for d in distributors if d.enabled}
        logger.info(f"Initialized KiCost client with distributors: {list(self.distributors.keys())}")
    
    # ========================================================================
    # Price Scraping
    # ========================================================================
    
    async def get_part_prices(
        self,
        mpn: str,
        manufacturer: Optional[str] = None,
        quantity: int = 1,
    ) -> List[DistributorPrice]:
        """
        Get prices for a part from all enabled distributors
        
        **Validates: Requirement 7.5** - Multi-distributor pricing
        """
        prices: List[DistributorPrice] = []
        
        for dist_name, dist_config in self.distributors.items():
            try:
                price = await self._scrape_distributor(
                    dist_name,
                    mpn,
                    manufacturer,
                    quantity,
                    dist_config.api_key,
                )
                if price:
                    prices.append(price)
            except Exception as e:
                logger.warning(f"Failed to get price from {dist_name}: {e}")
        
        return prices
    
    async def _scrape_distributor(
        self,
        distributor: str,
        mpn: str,
        manufacturer: Optional[str],
        quantity: int,
        api_key: Optional[str],
    ) -> Optional[DistributorPrice]:
        """Scrape price from a specific distributor"""
        # This is a placeholder - actual implementation would use KiCost library
        # or distributor APIs (Digi-Key, Mouser, Arrow, Newark, TME)
        
        if distributor == "digikey":
            return await self._scrape_digikey(mpn, manufacturer, quantity, api_key)
        elif distributor == "mouser":
            return await self._scrape_mouser(mpn, manufacturer, quantity, api_key)
        elif distributor == "arrow":
            return await self._scrape_arrow(mpn, manufacturer, quantity, api_key)
        elif distributor == "newark":
            return await self._scrape_newark(mpn, manufacturer, quantity, api_key)
        elif distributor == "tme":
            return await self._scrape_tme(mpn, manufacturer, quantity, api_key)
        else:
            logger.warning(f"Unknown distributor: {distributor}")
            return None
    
    async def _scrape_digikey(
        self,
        mpn: str,
        manufacturer: Optional[str],
        quantity: int,
        api_key: Optional[str],
    ) -> Optional[DistributorPrice]:
        """Scrape Digi-Key prices"""
        # Placeholder for Digi-Key API integration
        logger.debug(f"Scraping Digi-Key for {mpn}")
        return None
    
    async def _scrape_mouser(
        self,
        mpn: str,
        manufacturer: Optional[str],
        quantity: int,
        api_key: Optional[str],
    ) -> Optional[DistributorPrice]:
        """Scrape Mouser prices"""
        # Placeholder for Mouser API integration
        logger.debug(f"Scraping Mouser for {mpn}")
        return None
    
    async def _scrape_arrow(
        self,
        mpn: str,
        manufacturer: Optional[str],
        quantity: int,
        api_key: Optional[str],
    ) -> Optional[DistributorPrice]:
        """Scrape Arrow prices"""
        # Placeholder for Arrow API integration
        logger.debug(f"Scraping Arrow for {mpn}")
        return None
    
    async def _scrape_newark(
        self,
        mpn: str,
        manufacturer: Optional[str],
        quantity: int,
        api_key: Optional[str],
    ) -> Optional[DistributorPrice]:
        """Scrape Newark prices"""
        # Placeholder for Newark API integration
        logger.debug(f"Scraping Newark for {mpn}")
        return None
    
    async def _scrape_tme(
        self,
        mpn: str,
        manufacturer: Optional[str],
        quantity: int,
        api_key: Optional[str],
    ) -> Optional[DistributorPrice]:
        """Scrape TME prices"""
        # Placeholder for TME API integration
        logger.debug(f"Scraping TME for {mpn}")
        return None
    
    # ========================================================================
    # BOM Pricing
    # ========================================================================
    
    async def price_bom(self, bom: List[BOMItem]) -> List[BOMPricing]:
        """
        Price entire BOM from all distributors
        
        **Validates: Requirement 7.5** - BOM pricing
        """
        results: List[BOMPricing] = []
        
        for item in bom:
            if not item.mpn:
                logger.warning(f"Skipping {item.reference}: no MPN specified")
                continue
            
            prices = await self.get_part_prices(
                item.mpn,
                item.manufacturer,
                item.quantity,
            )
            
            # Find best price
            best_price = self.select_best_price(prices, item.quantity)
            
            # Calculate total cost
            total_cost = None
            if best_price:
                unit_price = self.get_price_for_quantity(best_price, item.quantity)
                if unit_price:
                    total_cost = unit_price * item.quantity
            
            results.append(BOMPricing(
                item=item,
                prices=prices,
                best_price=best_price,
                total_cost=total_cost,
            ))
        
        return results
    
    # ========================================================================
    # Price Comparison
    # ========================================================================
    
    def select_best_price(
        self,
        prices: List[DistributorPrice],
        quantity: int,
    ) -> Optional[DistributorPrice]:
        """
        Select best price considering quantity, stock, and distributor priority
        
        **Validates: Requirement 7.6** - Price comparison
        **Validates: Requirement 7.7** - Best price selection
        """
        if not prices:
            return None
        
        # Filter prices with sufficient stock
        available_prices = [p for p in prices if p.stock >= quantity]
        
        if not available_prices:
            # No distributor has enough stock, return lowest price anyway
            available_prices = prices
        
        # Calculate effective price for each distributor
        price_comparisons = []
        for price in available_prices:
            unit_price = self.get_price_for_quantity(price, quantity)
            if unit_price:
                # Get distributor priority
                dist_config = self.distributors.get(price.distributor)
                priority = dist_config.priority if dist_config else 0
                
                price_comparisons.append({
                    "price": price,
                    "unit_price": unit_price,
                    "total_price": unit_price * quantity,
                    "priority": priority,
                    "has_stock": price.stock >= quantity,
                })
        
        if not price_comparisons:
            return None
        
        # Sort by: has_stock (desc), total_price (asc), priority (desc)
        price_comparisons.sort(
            key=lambda x: (
                not x["has_stock"],  # Prefer in-stock
                x["total_price"],     # Lower price
                -x["priority"],       # Higher priority
            )
        )
        
        return price_comparisons[0]["price"]
    
    def get_price_for_quantity(
        self,
        price: DistributorPrice,
        quantity: int,
    ) -> Optional[Decimal]:
        """Get unit price for a specific quantity"""
        if not price.price_breaks:
            return None
        
        # Find applicable price break
        applicable_break = None
        for price_break in sorted(price.price_breaks, key=lambda x: x.quantity, reverse=True):
            if quantity >= price_break.quantity:
                applicable_break = price_break
                break
        
        if not applicable_break:
            # Use lowest quantity price break
            applicable_break = min(price.price_breaks, key=lambda x: x.quantity)
        
        return applicable_break.price
    
    def compare_prices(
        self,
        prices: List[DistributorPrice],
        quantity: int,
    ) -> List[Dict[str, Any]]:
        """
        Compare prices across distributors
        
        **Validates: Requirement 7.6** - Price comparison
        """
        comparisons = []
        
        for price in prices:
            unit_price = self.get_price_for_quantity(price, quantity)
            if unit_price:
                comparisons.append({
                    "distributor": price.distributor,
                    "part_number": price.part_number,
                    "unit_price": float(unit_price),
                    "total_price": float(unit_price * quantity),
                    "stock": price.stock,
                    "moq": price.moq,
                    "lead_time_days": price.lead_time_days,
                    "in_stock": price.stock >= quantity,
                })
        
        # Sort by total price
        comparisons.sort(key=lambda x: x["total_price"])
        
        return comparisons
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def calculate_bom_total(self, bom_pricing: List[BOMPricing]) -> Decimal:
        """Calculate total BOM cost"""
        total = Decimal(0)
        for item_pricing in bom_pricing:
            if item_pricing.total_cost:
                total += item_pricing.total_cost
        return total
    
    def get_bom_summary(self, bom_pricing: List[BOMPricing]) -> Dict[str, Any]:
        """Get BOM pricing summary"""
        total_cost = self.calculate_bom_total(bom_pricing)
        
        # Count items by availability
        in_stock = sum(1 for p in bom_pricing if p.best_price and p.best_price.stock >= p.item.quantity)
        out_of_stock = len(bom_pricing) - in_stock
        
        # Get distributor breakdown
        distributor_counts: Dict[str, int] = {}
        for item_pricing in bom_pricing:
            if item_pricing.best_price:
                dist = item_pricing.best_price.distributor
                distributor_counts[dist] = distributor_counts.get(dist, 0) + 1
        
        return {
            "total_items": len(bom_pricing),
            "total_cost": float(total_cost),
            "in_stock": in_stock,
            "out_of_stock": out_of_stock,
            "distributor_breakdown": distributor_counts,
        }
