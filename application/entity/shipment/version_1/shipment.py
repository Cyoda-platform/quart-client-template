from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Shipment(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Shipment"
    ENTITY_VERSION: ClassVar[int] = 1

    shipmentId: str = Field(..., description="Shipment ID")
    orderId: str = Field(..., description="Associated order ID")
    status: str = Field(default="PICKING", description="Shipment status")
    lines: List[Dict[str, Any]] = Field(
        default_factory=list, description="Shipment lines"
    )
    createdAt: Optional[str] = Field(None, description="Creation timestamp")
    updatedAt: Optional[str] = Field(None, description="Update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

