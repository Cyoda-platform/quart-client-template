from datetime import datetime, timezone
from typing import ClassVar, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order represents a buy/sell order in the institutional trading platform.

    Manages order lifecycle from creation through execution and settlement.
    States: initial_state -> created -> validated -> submitted -> executed -> settled -> completed
    """

    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    # Order identification
    order_id: str = Field(..., description="Unique order identifier")
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, MSFT)")
    side: str = Field(..., description="BUY or SELL")
    order_type: str = Field(..., description="MARKET, LIMIT, STOP, STOP_LIMIT")

    # Order quantities and pricing
    quantity: float = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(
        None, ge=0, description="Limit price for limit orders"
    )
    stop_price: Optional[float] = Field(
        None, ge=0, description="Stop price for stop orders"
    )

    # Order status and execution
    status: str = Field(default="pending", description="Order status")
    filled_quantity: float = Field(default=0, ge=0, description="Quantity filled")
    average_fill_price: Optional[float] = Field(
        None, ge=0, description="Average execution price"
    )

    # Risk and compliance
    account_id: str = Field(..., description="Trading account ID")
    trader_id: str = Field(..., description="Trader identifier")
    risk_limit_check: bool = Field(
        default=False, description="Risk limit validation passed"
    )
    compliance_check: bool = Field(
        default=False, description="Compliance validation passed"
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
        None, alias="submittedAt", description="Submission timestamp"
    )
    executed_at: Optional[str] = Field(
        None, alias="executedAt", description="Execution timestamp"
    )

    # Metadata
    execution_venue: Optional[str] = Field(None, description="Execution venue/exchange")
    execution_algorithm: Optional[str] = Field(
        None, description="Execution algorithm used"
    )
    notes: Optional[str] = Field(None, description="Order notes")

    ALLOWED_SIDES: ClassVar[List[str]] = ["BUY", "SELL"]
    ALLOWED_ORDER_TYPES: ClassVar[List[str]] = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v not in cls.ALLOWED_SIDES:
            raise ValueError(f"Side must be one of: {cls.ALLOWED_SIDES}")
        return v

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        if v not in cls.ALLOWED_ORDER_TYPES:
            raise ValueError(f"Order type must be one of: {cls.ALLOWED_ORDER_TYPES}")
        return v

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol must be non-empty")
        if len(v) > 10:
            raise ValueError("Symbol must be at most 10 characters")
        return v.upper()

    @model_validator(mode="after")
    def validate_order_logic(self) -> "Order":
        if self.order_type in ["LIMIT", "STOP_LIMIT"] and self.price is None:
            raise ValueError(f"{self.order_type} orders require a price")
        if self.order_type in ["STOP", "STOP_LIMIT"] and self.stop_price is None:
            raise ValueError(f"{self.order_type} orders require a stop_price")
        if self.filled_quantity > self.quantity:
            raise ValueError("Filled quantity cannot exceed order quantity")
        return self

    def is_fully_filled(self) -> bool:
        return self.filled_quantity >= self.quantity

    def is_partially_filled(self) -> bool:
        return 0 < self.filled_quantity < self.quantity

    def get_remaining_quantity(self) -> float:
        return self.quantity - self.filled_quantity

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
