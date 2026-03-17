"""
Order entity for institutional trading platform.

Manages order lifecycle: new -> submitted -> partially_filled -> filled/canceled/rejected
Supports market, limit, iceberg, stop-limit, FOK, IOC order types.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order represents a trading order in the institutional trading system.

    Manages order lifecycle with states: new -> submitted -> partially_filled ->
    filled/canceled/rejected. Supports multiple order types and venues.
    """

    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    # Order identification
    order_id: str = Field(..., description="Unique order identifier")
    client_order_id: Optional[str] = Field(
        default=None, alias="clientOrderId", description="Client-provided order ID"
    )

    # Instrument and account
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, EURUSD)")
    account_id: str = Field(..., alias="accountId", description="Trading account ID")
    legal_entity: str = Field(..., alias="legalEntity", description="Legal entity code")

    # Order parameters
    order_type: str = Field(
        ...,
        alias="orderType",
        description="Order type: market, limit, iceberg, stop_limit, FOK, IOC",
    )
    side: str = Field(..., description="Order side: BUY or SELL")
    quantity: float = Field(..., description="Order quantity")
    price: Optional[float] = Field(
        default=None, description="Limit price (if applicable)"
    )
    stop_price: Optional[float] = Field(
        default=None,
        alias="stopPrice",
        description="Stop price (for stop-limit orders)",
    )

    # Execution details
    filled_quantity: float = Field(
        default=0.0, alias="filledQuantity", description="Quantity filled so far"
    )
    average_fill_price: Optional[float] = Field(
        default=None, alias="averageFillPrice", description="Average execution price"
    )
    venue: Optional[str] = Field(
        default=None, description="Execution venue (LSE, Euronext, etc.)"
    )

    # Risk and compliance
    max_order_size_limit: Optional[float] = Field(
        default=None, alias="maxOrderSizeLimit", description="Pre-trade risk limit"
    )
    exposure_limit: Optional[float] = Field(
        default=None, alias="exposureLimit", description="Account exposure limit"
    )

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Order creation timestamp",
    )
    submitted_at: Optional[str] = Field(
        default=None, alias="submittedAt", description="Order submission timestamp"
    )
    filled_at: Optional[str] = Field(
        default=None, alias="filledAt", description="Order fill timestamp"
    )

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        """Validate order type"""
        valid_types = ["market", "limit", "iceberg", "stop_limit", "FOK", "IOC"]
        if v not in valid_types:
            raise ValueError(f"Order type must be one of: {valid_types}")
        return v

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate order side"""
        if v not in ["BUY", "SELL"]:
            raise ValueError("Side must be BUY or SELL")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        """Validate quantity is positive"""
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    def is_filled(self) -> bool:
        """Check if order is fully filled"""
        return self.filled_quantity >= self.quantity

    def is_partially_filled(self) -> bool:
        """Check if order is partially filled"""
        return 0 < self.filled_quantity < self.quantity

    def remaining_quantity(self) -> float:
        """Get remaining quantity to fill"""
        return max(0, self.quantity - self.filled_quantity)

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
