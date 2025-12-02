from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Product(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Product"
    ENTITY_VERSION: ClassVar[int] = 1

    sku: str = Field(..., description="Product SKU (unique)")
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Product description")
    price: float = Field(..., description="Base price")
    quantityAvailable: int = Field(..., description="Available quantity")
    category: str = Field(..., description="Product category")
    warehouseId: Optional[str] = Field(None, description="Warehouse ID")

    attributes: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Product attributes (brand, model, dimensions, weight, hazards, custom)",
    )
    localizations: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Localization data with locale-specific content",
    )
    media: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Media items (images, documents)",
    )
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Product options (axes, constraints)",
    )
    variants: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Product variants",
    )
    bundles: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Product bundles",
    )
    inventory: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Inventory data (nodes, policies)",
    )
    compliance: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Compliance data (docs, restrictions)",
    )
    relationships: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Product relationships (suppliers, related products)",
    )
    events: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Product events",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

