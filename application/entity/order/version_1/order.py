"""
Order entity for institutional trading platform.

Represents buy/sell orders with full lifecycle management.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order represents a buy/sell order in the trading system.

    State: initial_state -> created -> acked -> partially_filled -> filled
    """

    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    instrument_id: str = Field(..., alias="instrumentId", description="Instrument ID")
    order_type: str = Field(
        ...,
        alias="orderType",
        description="MARKET, LIMIT, STOP, STOP_LIMIT, FOK, IOC",
    )
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., description="Order quantity")
    price: Optional[float] = Field(default=None, description="Limit price")
    filled_quantity: float = Field(
        default=0.0, alias="filledQuantity", description="Quantity filled"
    )
    average_price: Optional[float] = Field(
        default=None, alias="averagePrice", description="Average execution price"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Creation timestamp",
    )
    routing_venue: Optional[str] = Field(
        default=None, alias="routingVenue", description="Routing venue"
    )

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        valid = {"MARKET", "LIMIT", "STOP", "STOP_LIMIT", "FOK", "IOC"}
        if v.upper() not in valid:
            raise ValueError(f"Invalid order type: {v}")
        return v.upper()

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v.upper() not in {"BUY", "SELL"}:
            raise ValueError("Side must be BUY or SELL")
        return v.upper()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v
