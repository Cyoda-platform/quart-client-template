"""
Order entity for institutional trading platform.

Represents an order lifecycle: initial_state -> submitted -> accepted -> partially_filled
-> filled -> cancelled -> completed
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order represents a trading order in the institutional trading platform.
    Manages order lifecycle from submission through execution and completion.
    """

    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., description="Account ID placing the order")
    instrument_id: str = Field(..., description="Security identifier (ticker/ISIN)")
    order_type: str = Field(
        ..., alias="orderType", description="Order type: LIMIT, MARKET, IOC, FOK, GTC"
    )
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(
        default=None, description="Limit price (null for market orders)"
    )
    filled_quantity: float = Field(
        default=0.0, alias="filledQuantity", description="Quantity filled so far"
    )
    avg_fill_price: Optional[float] = Field(
        default=None, alias="avgFillPrice", description="Average fill price"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Order creation timestamp",
    )
    updated_at: Optional[str] = Field(
        default=None, alias="updatedAt", description="Last update timestamp"
    )

    ORDER_TYPES: ClassVar[List[str]] = ["LIMIT", "MARKET", "IOC", "FOK", "GTC"]
    SIDES: ClassVar[List[str]] = ["BUY", "SELL"]

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        if v not in cls.ORDER_TYPES:
            raise ValueError(f"Order type must be one of: {cls.ORDER_TYPES}")
        return v

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v not in cls.SIDES:
            raise ValueError(f"Side must be one of: {cls.SIDES}")
        return v

    model_config = ConfigDict(
        populate_by_name=True, validate_assignment=True, extra="allow"
    )
