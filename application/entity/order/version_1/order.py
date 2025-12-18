"""
Order entity for trading platform.

Represents client orders with full lifecycle management from submission
through execution, cancellation, or rejection.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Represents a client order in the trading system.
    
    Manages order lifecycle: initial_state -> submitted -> ack -> 
    partial_fill -> filled -> settled (or cancelled/rejected)
    """

    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    client_order_id: str = Field(
        ..., alias="clientOrderId", description="Client-assigned order ID"
    )
    account_id: str = Field(..., alias="accountId", description="Account placing order")
    symbol: str = Field(..., description="Instrument symbol")
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., description="Order quantity")
    order_type: str = Field(
        ..., alias="orderType", description="MARKET, LIMIT, STOP, etc."
    )
    price: Optional[float] = Field(
        default=None, description="Limit price (if applicable)"
    )
    stop_price: Optional[float] = Field(
        default=None, alias="stopPrice", description="Stop price (if applicable)"
    )
    time_in_force: str = Field(
        default="GTC", alias="timeInForce", description="GTC, IOC, FOK, etc."
    )
    filled_quantity: float = Field(
        default=0.0, alias="filledQuantity", description="Quantity filled so far"
    )
    avg_fill_price: Optional[float] = Field(
        default=None, alias="avgFillPrice", description="Average fill price"
    )
    status: str = Field(default="NEW", description="Order status")
    rejection_reason: Optional[str] = Field(
        default=None, alias="rejectionReason", description="Reason if rejected"
    )
    created_at: str = Field(..., alias="createdAt", description="Order creation time")
    updated_at: Optional[str] = Field(
        default=None, alias="updatedAt", description="Last update time"
    )

    def is_open(self) -> bool:
        return self.state in ("submitted", "ack", "partial_fill")

    def is_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    def remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity

