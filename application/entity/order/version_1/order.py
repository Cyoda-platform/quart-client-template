from typing import ClassVar, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order represents a trading order with full lifecycle management.
    Handles validation, routing, execution, and reporting.
    """

    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    order_id: str = Field(..., alias="orderId", description="Unique order identifier")
    account_id: str = Field(..., alias="accountId", description="Account ID")
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="BUY or SELL")
    order_type: str = Field(..., alias="orderType", description="LIMIT, MARKET, etc.")
    quantity: int = Field(..., description="Order quantity")
    price: float = Field(..., description="Order price")
    status: str = Field(..., description="Order status")
    created_at: str = Field(..., alias="createdAt", description="Creation timestamp")
    executed_qty: int = Field(
        default=0, alias="executedQty", description="Executed quantity"
    )
    executed_price: Optional[float] = Field(
        default=None, alias="executedPrice", description="Execution price"
    )
    executed_at: Optional[str] = Field(
        default=None, alias="executedAt", description="Execution timestamp"
    )
    cancelled_qty: int = Field(
        default=0, alias="cancelledQty", description="Cancelled quantity"
    )
    cancelled_at: Optional[str] = Field(
        default=None, alias="cancelledAt", description="Cancellation timestamp"
    )
    time_in_force: str = Field(
        default="DAY", alias="timeInForce", description="Time in force"
    )
    limit_price: Optional[float] = Field(
        default=None, alias="limitPrice", description="Limit price"
    )
    order_value: float = Field(..., alias="orderValue", description="Total order value")
    commission: float = Field(default=0.0, description="Commission")
    fees: float = Field(default=0.0, description="Fees")
    total_cost: float = Field(..., alias="totalCost", description="Total cost")
    notes: Optional[str] = Field(default=None, description="Order notes")

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Order ID must be non-empty")
        return v.strip()

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v.upper() not in ["BUY", "SELL"]:
            raise ValueError("Side must be BUY or SELL")
        return v.upper()

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        valid_types = ["LIMIT", "MARKET", "STOP", "STOP_LIMIT"]
        if v.upper() not in valid_types:
            raise ValueError(f"Order type must be one of {valid_types}")
        return v.upper()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("price", "order_value", "total_cost")
    @classmethod
    def validate_amounts(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
