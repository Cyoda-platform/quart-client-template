"""
Order entity for trading platform.

Represents a trading order submitted to the system with order lifecycle
management through workflow states.
"""

from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order entity representing a trading order.

    Supports buy/sell orders with various order types (LIMIT, MARKET, etc.)
    and tracks order lifecycle from submission through fills and cancellations.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core order fields
    instrument_id: str = Field(
        ..., alias="instrumentId", description="ID of the instrument being traded"
    )
    side: str = Field(..., description="Order side: BUY or SELL")
    order_type: str = Field(
        ..., alias="orderType", description="Order type: LIMIT, MARKET, STOP, etc."
    )
    quantity: float = Field(..., description="Quantity to trade")
    price: Optional[float] = Field(
        default=None, description="Limit price for LIMIT orders"
    )
    account_id: str = Field(
        ..., alias="accountId", description="Account ID placing the order"
    )
    submitted_by: str = Field(
        ..., alias="submittedBy", description="User/system that submitted the order"
    )
    submitted_at: str = Field(
        ..., alias="submittedAt", description="Timestamp when order was submitted (ISO 8601)"
    )

    # Order execution tracking
    filled_quantity: Optional[float] = Field(
        default=0.0,
        alias="filledQuantity",
        description="Quantity filled so far",
    )
    average_fill_price: Optional[float] = Field(
        default=None,
        alias="averageFillPrice",
        description="Average price of fills",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
