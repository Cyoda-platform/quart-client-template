from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order represents an order in the trading platform.

    Manages order lifecycle: initial_state -> created -> validated -> submitted -> filled/cancelled
    """

    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    client_id: str = Field(..., description="Client identifier")
    account: str = Field(..., description="Trading account")
    instrument: str = Field(..., description="Instrument symbol (e.g., AAPL)")
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., gt=0, description="Order quantity")
    order_type: str = Field(..., description="MARKET, LIMIT, or STOP")
    price: Optional[float] = Field(
        default=None, ge=0, description="Order price (required for LIMIT/STOP)"
    )
    time_in_force: str = Field(
        default="GTC", description="IOC, FOK, or GTC"
    )
    route: str = Field(default="DEFAULT", description="Execution route")

    client_order_id: Optional[str] = Field(
        default=None, alias="clientOrderId", description="Client-assigned order ID"
    )
    order_id: Optional[str] = Field(
        default=None, alias="orderId", description="System-assigned order ID"
    )

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

    filled_quantity: float = Field(
        default=0, alias="filledQuantity", description="Quantity filled"
    )
    remaining_quantity: Optional[float] = Field(
        default=None, alias="remainingQuantity", description="Remaining quantity"
    )

    status: Optional[str] = Field(
        default=None, description="Order status (PENDING, SUBMITTED, FILLED, CANCELLED)"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v not in ["BUY", "SELL"]:
            raise ValueError("Side must be BUY or SELL")
        return v

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        if v not in ["MARKET", "LIMIT", "STOP"]:
            raise ValueError("Order type must be MARKET, LIMIT, or STOP")
        return v

    @field_validator("time_in_force")
    @classmethod
    def validate_time_in_force(cls, v: str) -> str:
        if v not in ["IOC", "FOK", "GTC"]:
            raise ValueError("Time in force must be IOC, FOK, or GTC")
        return v

    def to_api_response(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        return data

