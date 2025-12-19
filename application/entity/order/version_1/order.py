from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order represents a trading order in the system.
    State transitions: initial_state -> new -> open -> partial_fill -> filled/cancelled/rejected
    """

    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, BTC-USD)")
    order_type: str = Field(..., description="Order type: MARKET, LIMIT, STOP")
    side: str = Field(..., description="Order side: BUY or SELL")
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, description="Limit price for LIMIT orders")
    account_id: str = Field(..., description="Account ID placing the order")
    venue_id: str = Field(..., description="Venue ID for execution")
    filled_quantity: float = Field(
        default=0, ge=0, description="Quantity filled so far"
    )
    average_fill_price: Optional[float] = Field(
        None, description="Average price of fills"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Order creation timestamp",
    )
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        if v not in ["MARKET", "LIMIT", "STOP"]:
            raise ValueError("order_type must be MARKET, LIMIT, or STOP")
        return v

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v not in ["BUY", "SELL"]:
            raise ValueError("side must be BUY or SELL")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
