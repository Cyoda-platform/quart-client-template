from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class CartLine(CyodaEntity):
    sku: str = Field(..., description="Product SKU")
    name: str = Field(..., description="Product name")
    price: float = Field(..., description="Unit price")
    qty: int = Field(..., description="Quantity")


class GuestContact(CyodaEntity):
    name: Optional[str] = Field(None, description="Guest name")
    email: Optional[str] = Field(None, description="Guest email")
    phone: Optional[str] = Field(None, description="Guest phone")
    address: Optional[Dict[str, str]] = Field(None, description="Guest address")


class Cart(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Cart"
    ENTITY_VERSION: ClassVar[int] = 1

    cartId: str = Field(..., description="Cart ID")
    status: str = Field(default="NEW", description="Cart status")
    lines: List[Dict[str, Any]] = Field(default_factory=list, description="Cart lines")
    totalItems: int = Field(default=0, description="Total items in cart")
    grandTotal: float = Field(default=0.0, description="Grand total")
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

