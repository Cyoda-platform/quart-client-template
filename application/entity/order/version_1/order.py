from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    order_id: str = Field(..., description="Unique business ID for the order")
    account_id: str = Field(..., description="Account ID")
    instrument_id: str = Field(..., description="Instrument ID (technical ID)")
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., description="Order quantity")
    price: Optional[float] = Field(default=None, description="Limit price")
    order_type: str = Field(..., description="MARKET, LIMIT, etc.", alias="type")

    # Status tracking
    status: str = Field(
        default="PENDING",
        description="Order status (PENDING, ACCEPTED, REJECTED, FILLED, CANCELLED)",
    )
    filled_quantity: float = Field(default=0.0, description="Filled quantity")

    # Internal workflow fields
    validation_status: Optional[str] = Field(
        default=None, description="Internal validation status: PASS/FAIL"
    )
    rejection_reason: Optional[str] = Field(
        default=None, description="Reason for rejection"
    )
