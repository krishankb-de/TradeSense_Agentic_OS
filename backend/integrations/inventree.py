"""
InvenTree API Integration

Provides REST API client for InvenTree inventory management system.
Supports inventory queries, updates, and part searches.

**Validates: Requirements 7.1, 7.2, 7.9**
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class InvenTreeConfig(BaseModel):
    """InvenTree API configuration"""
    
    base_url: str = Field(..., description="InvenTree API base URL")
    api_token: str = Field(..., description="API authentication token")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")


class PartInfo(BaseModel):
    """Part information from InvenTree"""
    
    pk: int = Field(..., description="Primary key")
    name: str = Field(..., description="Part name")
    description: str = Field(default="", description="Part description")
    category: Optional[str] = Field(None, description="Part category")
    ipn: Optional[str] = Field(None, description="Internal part number")
    revision: Optional[str] = Field(None, description="Part revision")
    active: bool = Field(default=True, description="Part is active")
    in_stock: int = Field(default=0, description="Total stock quantity")
    available: int = Field(default=0, description="Available quantity")
    on_order: int = Field(default=0, description="Quantity on order")
    minimum_stock: int = Field(default=0, description="Minimum stock level")
    units: Optional[str] = Field(None, description="Stock units")
    notes: Optional[str] = Field(None, description="Part notes")
    link: Optional[str] = Field(None, description="External link")
    image: Optional[str] = Field(None, description="Part image URL")


class StockLocation(BaseModel):
    """Stock location information"""
    
    pk: int
    name: str
    description: str = ""
    parent: Optional[int] = None
    pathstring: str = ""
    items: int = 0


class StockItem(BaseModel):
    """Stock item information"""
    
    pk: int
    part: int
    part_name: str = ""
    location: Optional[int] = None
    location_name: str = ""
    quantity: float
    serial: Optional[str] = None
    batch: Optional[str] = None
    status: int = 10  # 10 = OK
    notes: Optional[str] = None


class InvenTreeClient:
    """
    InvenTree REST API Client
    
    **Validates: Requirement 7.1** - Inventory management integration
    **Validates: Requirement 7.2** - Real-time inventory queries
    **Validates: Requirement 7.9** - Parts availability tracking
    """
    
    def __init__(self, config: InvenTreeConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={
                "Authorization": f"Token {config.api_token}",
                "Content-Type": "application/json",
            },
            timeout=config.timeout,
            verify=config.verify_ssl,
        )
        logger.info(f"Initialized InvenTree client: {config.base_url}")
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # ========================================================================
    # Part Operations
    # ========================================================================
    
    async def search_parts(
        self,
        search: Optional[str] = None,
        category: Optional[int] = None,
        active: bool = True,
        limit: int = 100,
    ) -> List[PartInfo]:
        """
        Search for parts
        
        **Validates: Requirement 7.1** - Part search functionality
        """
        params: Dict[str, Any] = {
            "active": active,
            "limit": limit,
        }
        
        if search:
            params["search"] = search
        if category:
            params["category"] = category
        
        response = await self.client.get("/api/part/", params=params)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        return [PartInfo(**part) for part in results]
    
    async def get_part(self, part_id: int) -> PartInfo:
        """
        Get part by ID
        
        **Validates: Requirement 7.1** - Part information retrieval
        """
        response = await self.client.get(f"/api/part/{part_id}/")
        response.raise_for_status()
        
        return PartInfo(**response.json())
    
    async def get_part_by_ipn(self, ipn: str) -> Optional[PartInfo]:
        """Get part by internal part number"""
        parts = await self.search_parts(search=ipn, limit=1)
        return parts[0] if parts else None
    
    async def get_part_stock_level(self, part_id: int) -> Dict[str, int]:
        """
        Get stock levels for a part
        
        **Validates: Requirement 7.2** - Real-time inventory queries
        """
        part = await self.get_part(part_id)
        
        return {
            "in_stock": part.in_stock,
            "available": part.available,
            "on_order": part.on_order,
            "minimum_stock": part.minimum_stock,
        }
    
    async def check_part_availability(self, part_id: int, required_quantity: int) -> bool:
        """
        Check if part is available in required quantity
        
        **Validates: Requirement 7.9** - Parts availability tracking
        """
        stock = await self.get_part_stock_level(part_id)
        return stock["available"] >= required_quantity
    
    # ========================================================================
    # Stock Operations
    # ========================================================================
    
    async def get_stock_items(
        self,
        part_id: Optional[int] = None,
        location: Optional[int] = None,
        in_stock: bool = True,
    ) -> List[StockItem]:
        """Get stock items"""
        params: Dict[str, Any] = {}
        
        if part_id:
            params["part"] = part_id
        if location:
            params["location"] = location
        if in_stock:
            params["in_stock"] = "true"
        
        response = await self.client.get("/api/stock/", params=params)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        return [StockItem(**item) for item in results]
    
    async def update_stock_quantity(
        self,
        stock_item_id: int,
        quantity: float,
        notes: Optional[str] = None,
    ) -> StockItem:
        """
        Update stock item quantity
        
        **Validates: Requirement 7.2** - Inventory updates
        """
        payload = {
            "quantity": quantity,
        }
        if notes:
            payload["notes"] = notes
        
        response = await self.client.patch(
            f"/api/stock/{stock_item_id}/",
            json=payload,
        )
        response.raise_for_status()
        
        return StockItem(**response.json())
    
    async def add_stock(
        self,
        part_id: int,
        quantity: float,
        location: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> StockItem:
        """Add stock for a part"""
        payload = {
            "part": part_id,
            "quantity": quantity,
        }
        if location:
            payload["location"] = location
        if notes:
            payload["notes"] = notes
        
        response = await self.client.post("/api/stock/", json=payload)
        response.raise_for_status()
        
        return StockItem(**response.json())
    
    async def remove_stock(
        self,
        stock_item_id: int,
        quantity: float,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Remove stock from a stock item"""
        payload = {
            "quantity": quantity,
        }
        if notes:
            payload["notes"] = notes
        
        response = await self.client.post(
            f"/api/stock/{stock_item_id}/remove/",
            json=payload,
        )
        response.raise_for_status()
        
        return response.json()
    
    # ========================================================================
    # Location Operations
    # ========================================================================
    
    async def get_stock_locations(
        self,
        parent: Optional[int] = None,
    ) -> List[StockLocation]:
        """Get stock locations"""
        params: Dict[str, Any] = {}
        if parent:
            params["parent"] = parent
        
        response = await self.client.get("/api/stock/location/", params=params)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("results", [])
        
        return [StockLocation(**loc) for loc in results]
    
    async def get_stock_location(self, location_id: int) -> StockLocation:
        """Get stock location by ID"""
        response = await self.client.get(f"/api/stock/location/{location_id}/")
        response.raise_for_status()
        
        return StockLocation(**response.json())
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    async def get_low_stock_parts(self, threshold: Optional[int] = None) -> List[PartInfo]:
        """
        Get parts with stock below minimum level
        
        **Validates: Requirement 7.9** - Low stock alerts
        """
        # Get all active parts
        parts = await self.search_parts(active=True, limit=1000)
        
        # Filter parts below minimum stock
        low_stock = []
        for part in parts:
            if threshold:
                if part.in_stock < threshold:
                    low_stock.append(part)
            else:
                if part.minimum_stock > 0 and part.in_stock < part.minimum_stock:
                    low_stock.append(part)
        
        return low_stock
    
    async def get_parts_on_order(self) -> List[PartInfo]:
        """Get parts with outstanding orders"""
        parts = await self.search_parts(active=True, limit=1000)
        return [part for part in parts if part.on_order > 0]
    
    async def health_check(self) -> bool:
        """Check if InvenTree API is accessible"""
        try:
            response = await self.client.get("/api/")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"InvenTree health check failed: {e}")
            return False
