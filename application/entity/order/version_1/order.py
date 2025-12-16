from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order represents a trading order in the system.

    Tracks order lifecycle from creation through execution including
    pricing, quantity, execution type, and current status.
    """

    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    order_id: str = Field(..., description="Unique order identifier")
    client_id: str = Field(..., description="Client/account identifier")
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, BTC/USD)")
    side: str = Field(..., description="Order side: BUY or SELL")
    type: str = Field(..., description="Order type: MARKET, LIMIT, STOP, STOP_LIMIT")
    price: Optional[float] = Field(
        None, description="Limit price (required for LIMIT orders)"
    )
    quantity: float = Field(..., description="Order quantity")
    time_in_force: str = Field(
        default="GTC",
        description="Time in force: GTC (Good-Till-Cancel), IOC (Immediate-Or-Cancel), FOK (Fill-Or-Kill)",
    )
    status: str = Field(
        default="PENDING",
        description="Order status: PENDING, ACCEPTED, REJECTED, FILLED, PARTIALLY_FILLED, CANCELLED",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Order creation timestamp (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        None, description="Last update timestamp (ISO 8601 format)"
    )

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate order side"""
        if v not in ("BUY", "SELL"):
            raise ValueError("Side must be BUY or SELL")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate order type"""
        valid_types = ("MARKET", "LIMIT", "STOP", "STOP_LIMIT")
        if v not in valid_types:
            raise ValueError(f"Type must be one of: {valid_types}")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        """Validate quantity is positive"""
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    def is_limit_order(self) -> bool:
        """Check if order is a limit order"""
        return self.type in ("LIMIT", "STOP_LIMIT")

    def is_filled(self) -> bool:
        """Check if order is fully filled"""
        return self.status == "FILLED"

    def is_active(self) -> bool:
        """Check if order is still active"""
        return self.status in ("PENDING", "ACCEPTED", "PARTIALLY_FILLED")
