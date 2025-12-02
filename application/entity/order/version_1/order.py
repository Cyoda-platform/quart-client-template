from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    orderId: str = Field(..., description="Order ID")
    orderNumber: str = Field(..., description="Order number (short ULID)")
    status: str = Field(default="WAITING_TO_FULFILL", description="Order status")
    lines: List[Dict[str, Any]] = Field(default_factory=list, description="Order lines")
    totals: Optional[Dict[str, Any]] = Field(
        None, description="Order totals (items, grand)"
    )
    guestContact: Optional[Dict[str, Any]] = Field(
        None, description="Guest contact information"
    )
    createdAt: Optional[str] = Field(None, description="Creation timestamp")
    updatedAt: Optional[str] = Field(None, description="Update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
