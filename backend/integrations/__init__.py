"""
Integration modules for external services and APIs.

Provides clients for:
- InvenTree (inventory management)
- Part-DB (component specifications)
- KiCost (distributor pricing)
- Kabaun (carbon tracking)

**Validates: Requirements 7.1-7.9, 8.1-8.5**
"""

from .inventree import InvenTreeClient, InvenTreeConfig, PartInfo, StockItem
from .partdb import PartDBClient, PartDBConfig, ComponentSpec, KiCadSymbol, KiCadFootprint
from .kicost import KiCostClient, DistributorConfig, BOMItem, BOMPricing, DistributorPrice
from .kabaun import KabaunClient, EmissionCalculation, EmissionSource, EmissionDataset, VehicleType

__all__ = [
    # InvenTree
    "InvenTreeClient",
    "InvenTreeConfig",
    "PartInfo",
    "StockItem",
    # Part-DB
    "PartDBClient",
    "PartDBConfig",
    "ComponentSpec",
    "KiCadSymbol",
    "KiCadFootprint",
    # KiCost
    "KiCostClient",
    "DistributorConfig",
    "BOMItem",
    "BOMPricing",
    "DistributorPrice",
    # Kabaun
    "KabaunClient",
    "EmissionCalculation",
    "EmissionSource",
    "EmissionDataset",
    "VehicleType",
]
