"""
Part-DB API Integration

Provides REST API client for Part-DB component specification database.
Supports component queries, KiCad symbol/footprint retrieval.

**Validates: Requirements 7.3, 7.4**
"""

import logging
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PartDBConfig(BaseModel):
    """Part-DB API configuration"""
    
    base_url: str = Field(..., description="Part-DB API base URL")
    api_token: Optional[str] = Field(None, description="API authentication token")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")


class ComponentSpec(BaseModel):
    """Component specification from Part-DB"""
    
    id: int = Field(..., description="Component ID")
    name: str = Field(..., description="Component name")
    description: str = Field(default="", description="Component description")
    category: Optional[str] = Field(None, description="Component category")
    manufacturer: Optional[str] = Field(None, description="Manufacturer name")
    mpn: Optional[str] = Field(None, description="Manufacturer part number")
    datasheet_url: Optional[str] = Field(None, description="Datasheet URL")
    footprint: Optional[str] = Field(None, description="PCB footprint")
    symbol: Optional[str] = Field(None, description="Schematic symbol")
    value: Optional[str] = Field(None, description="Component value")
    package: Optional[str] = Field(None, description="Component package")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Component parameters")
    tags: List[str] = Field(default_factory=list, description="Component tags")


class KiCadSymbol(BaseModel):
    """KiCad schematic symbol"""
    
    name: str
    library: str
    description: str = ""
    keywords: List[str] = Field(default_factory=list)
    datasheet: Optional[str] = None
    pins: List[Dict[str, Any]] = Field(default_factory=list)


class KiCadFootprint(BaseModel):
    """KiCad PCB footprint"""
    
    name: str
    library: str
    description: str = ""
    tags: List[str] = Field(default_factory=list)
    pads: List[Dict[str, Any]] = Field(default_factory=list)


class PartDBClient:
    """
    Part-DB REST API Client
    
    **Validates: Requirement 7.3** - Component specification database
    **Validates: Requirement 7.4** - KiCad symbol/footprint retrieval
    """
    
    def __init__(self, config: PartDBConfig):
        self.config = config
        headers = {"Content-Type": "application/json"}
        if config.api_token:
            headers["Authorization"] = f"Bearer {config.api_token}"
        
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers=headers,
            timeout=config.timeout,
            verify=config.verify_ssl,
        )
        logger.info(f"Initialized Part-DB client: {config.base_url}")
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # ========================================================================
    # Component Operations
    # ========================================================================
    
    async def search_components(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        manufacturer: Optional[str] = None,
        limit: int = 100,
    ) -> List[ComponentSpec]:
        """
        Search for components
        
        **Validates: Requirement 7.3** - Component search
        """
        params: Dict[str, Any] = {"limit": limit}
        
        if search:
            params["search"] = search
        if category:
            params["category"] = category
        if manufacturer:
            params["manufacturer"] = manufacturer
        
        response = await self.client.get("/api/parts", params=params)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("data", [])
        
        return [ComponentSpec(**comp) for comp in results]
    
    async def get_component(self, component_id: int) -> ComponentSpec:
        """
        Get component by ID
        
        **Validates: Requirement 7.3** - Component specification retrieval
        """
        response = await self.client.get(f"/api/parts/{component_id}")
        response.raise_for_status()
        
        return ComponentSpec(**response.json())
    
    async def get_component_by_mpn(self, mpn: str) -> Optional[ComponentSpec]:
        """Get component by manufacturer part number"""
        components = await self.search_components(search=mpn, limit=1)
        return components[0] if components else None
    
    async def get_component_parameters(self, component_id: int) -> Dict[str, Any]:
        """
        Get component parameters (resistance, capacitance, voltage, etc.)
        
        **Validates: Requirement 7.3** - Component specifications
        """
        component = await self.get_component(component_id)
        return component.parameters
    
    # ========================================================================
    # KiCad Integration
    # ========================================================================
    
    async def get_kicad_symbol(self, component_id: int) -> Optional[KiCadSymbol]:
        """
        Get KiCad schematic symbol for component
        
        **Validates: Requirement 7.4** - KiCad symbol retrieval
        """
        response = await self.client.get(f"/api/parts/{component_id}/kicad/symbol")
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        data = response.json()
        
        return KiCadSymbol(**data)
    
    async def get_kicad_footprint(self, component_id: int) -> Optional[KiCadFootprint]:
        """
        Get KiCad PCB footprint for component
        
        **Validates: Requirement 7.4** - KiCad footprint retrieval
        """
        response = await self.client.get(f"/api/parts/{component_id}/kicad/footprint")
        
        if response.status_code == 404:
            return None
        
        response.raise_for_status()
        data = response.json()
        
        return KiCadFootprint(**data)
    
    async def search_kicad_symbols(
        self,
        search: str,
        library: Optional[str] = None,
    ) -> List[KiCadSymbol]:
        """
        Search for KiCad symbols
        
        **Validates: Requirement 7.4** - Symbol search
        """
        params: Dict[str, Any] = {"search": search}
        if library:
            params["library"] = library
        
        response = await self.client.get("/api/kicad/symbols", params=params)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("data", [])
        
        return [KiCadSymbol(**sym) for sym in results]
    
    async def search_kicad_footprints(
        self,
        search: str,
        library: Optional[str] = None,
    ) -> List[KiCadFootprint]:
        """
        Search for KiCad footprints
        
        **Validates: Requirement 7.4** - Footprint search
        """
        params: Dict[str, Any] = {"search": search}
        if library:
            params["library"] = library
        
        response = await self.client.get("/api/kicad/footprints", params=params)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("data", [])
        
        return [KiCadFootprint(**fp) for fp in results]
    
    # ========================================================================
    # Category Operations
    # ========================================================================
    
    async def list_categories(self) -> List[Dict[str, Any]]:
        """List all component categories"""
        response = await self.client.get("/api/categories")
        response.raise_for_status()
        
        data = response.json()
        return data.get("data", [])
    
    async def get_components_by_category(self, category: str) -> List[ComponentSpec]:
        """Get all components in a category"""
        return await self.search_components(category=category, limit=1000)
    
    # ========================================================================
    # Manufacturer Operations
    # ========================================================================
    
    async def list_manufacturers(self) -> List[Dict[str, Any]]:
        """List all manufacturers"""
        response = await self.client.get("/api/manufacturers")
        response.raise_for_status()
        
        data = response.json()
        return data.get("data", [])
    
    async def get_components_by_manufacturer(
        self,
        manufacturer: str,
    ) -> List[ComponentSpec]:
        """Get all components from a manufacturer"""
        return await self.search_components(manufacturer=manufacturer, limit=1000)
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    async def find_alternative_components(
        self,
        component_id: int,
        match_parameters: bool = True,
    ) -> List[ComponentSpec]:
        """
        Find alternative/compatible components
        
        **Validates: Requirement 7.3** - Alternative component suggestions
        """
        # Get original component
        original = await self.get_component(component_id)
        
        # Search for similar components in same category
        alternatives = await self.search_components(
            category=original.category,
            limit=50,
        )
        
        # Filter out the original component
        alternatives = [c for c in alternatives if c.id != component_id]
        
        if match_parameters and original.parameters:
            # Filter by matching key parameters
            filtered = []
            for alt in alternatives:
                if self._parameters_match(original.parameters, alt.parameters):
                    filtered.append(alt)
            alternatives = filtered
        
        return alternatives
    
    def _parameters_match(
        self,
        params1: Dict[str, Any],
        params2: Dict[str, Any],
        tolerance: float = 0.1,
    ) -> bool:
        """Check if component parameters match within tolerance"""
        # Check key parameters (resistance, capacitance, voltage, etc.)
        key_params = ["resistance", "capacitance", "voltage", "current", "power"]
        
        for param in key_params:
            if param in params1 and param in params2:
                val1 = float(params1[param])
                val2 = float(params2[param])
                
                # Check if values are within tolerance
                if abs(val1 - val2) / val1 > tolerance:
                    return False
        
        return True
    
    async def get_component_datasheet(self, component_id: int) -> Optional[str]:
        """Get component datasheet URL"""
        component = await self.get_component(component_id)
        return component.datasheet_url
    
    async def health_check(self) -> bool:
        """Check if Part-DB API is accessible"""
        try:
            response = await self.client.get("/api/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Part-DB health check failed: {e}")
            return False
