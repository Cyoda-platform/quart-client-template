"""
Order Entity for Real-Time Trading Platform

Represents trading orders with lifecycle management, order types, and execution tracking
for equities and derivatives trading.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order entity represents trading orders with lifecycle management and execution tracking.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> validated -> risk_checked -> submitted -> filled/cancelled
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    order_id: str = Field(..., alias="orderId", description="Business order identifier")
    symbol: str = Field(..., description="Trading symbol")
    order_type: str = Field(
        ...,
        alias="orderType",
        description="Order type: MARKET, LIMIT, STOP, STOP_LIMIT",
    )
    side: str = Field(..., description="Order side: BUY or SELL")
    quantity: int = Field(..., description="Order quantity")
    portfolio_id: str = Field(
        ..., alias="portfolioId", description="Associated portfolio identifier"
    )
    time_in_force: str = Field(
        ..., alias="timeInForce", description="Time in force: DAY, GTC, IOC, FOK"
    )

    # Optional price fields (required for limit/stop orders)
    price: Optional[float] = Field(
        default=None,
        description="Limit/stop price (required for LIMIT, STOP, STOP_LIMIT orders)",
    )
    stop_price: Optional[float] = Field(
        default=None,
        alias="stopPrice",
        description="Stop price (required for STOP, STOP_LIMIT orders)",
    )

    # Execution tracking fields
    filled_quantity: int = Field(
        default=0, alias="filledQuantity", description="Executed quantity"
    )
    remaining_quantity: Optional[int] = Field(
        default=None,
        alias="remainingQuantity",
        description="Remaining quantity to be filled",
    )
    average_fill_price: Optional[float] = Field(
        default=None, alias="averageFillPrice", description="Average execution price"
    )

    # Order metadata
    order_source: Optional[str] = Field(
        default="API",
        alias="orderSource",
        description="Source of the order (API, GUI, etc.)",
    )
    client_order_id: Optional[str] = Field(
        default=None,
        alias="clientOrderId",
        description="Client-provided order identifier",
    )

    # Processing-related fields
    risk_check_result: Optional[Dict[str, Any]] = Field(
        default=None, alias="riskCheckResult", description="Result of risk checks"
    )
    execution_data: Optional[Dict[str, Any]] = Field(
        default=None, alias="executionData", description="Execution-related data"
    )

    # Validation constants
    ALLOWED_ORDER_TYPES: ClassVar[List[str]] = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]
    ALLOWED_SIDES: ClassVar[List[str]] = ["BUY", "SELL"]
    ALLOWED_TIME_IN_FORCE: ClassVar[List[str]] = ["DAY", "GTC", "IOC", "FOK"]

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        """Validate order ID format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Order ID must be non-empty")
        if len(v) > 50:
            raise ValueError("Order ID must be at most 50 characters long")
        return v.strip()

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate trading symbol format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol must be non-empty")
        if len(v) > 20:
            raise ValueError("Symbol must be at most 20 characters long")
        return v.strip().upper()

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        """Validate order type"""
        if v not in cls.ALLOWED_ORDER_TYPES:
            raise ValueError(f"Order type must be one of: {cls.ALLOWED_ORDER_TYPES}")
        return v

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate order side"""
        if v not in cls.ALLOWED_SIDES:
            raise ValueError(f"Order side must be one of: {cls.ALLOWED_SIDES}")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Validate quantity is positive"""
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("portfolio_id")
    @classmethod
    def validate_portfolio_id(cls, v: str) -> str:
        """Validate portfolio ID format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Portfolio ID must be non-empty")
        return v.strip()

    @field_validator("time_in_force")
    @classmethod
    def validate_time_in_force(cls, v: str) -> str:
        """Validate time in force"""
        if v not in cls.ALLOWED_TIME_IN_FORCE:
            raise ValueError(
                f"Time in force must be one of: {cls.ALLOWED_TIME_IN_FORCE}"
            )
        return v

    @field_validator("price", "stop_price")
    @classmethod
    def validate_prices(cls, v: Optional[float]) -> Optional[float]:
        """Validate price fields are positive"""
        if v is not None and v <= 0:
            raise ValueError("Prices must be positive")
        return v

    @field_validator("filled_quantity")
    @classmethod
    def validate_filled_quantity(cls, v: int) -> int:
        """Validate filled quantity is non-negative"""
        if v < 0:
            raise ValueError("Filled quantity must be non-negative")
        return v

    @model_validator(mode="after")
    def validate_order_logic(self) -> "Order":
        """Validate order business logic"""
        # Price requirements based on order type
        if self.order_type in ["LIMIT", "STOP_LIMIT"] and self.price is None:
            raise ValueError(f"{self.order_type} orders require a price")

        if self.order_type in ["STOP", "STOP_LIMIT"] and self.stop_price is None:
            raise ValueError(f"{self.order_type} orders require a stop price")

        # Validate filled quantity doesn't exceed total quantity
        if self.filled_quantity > self.quantity:
            raise ValueError("Filled quantity cannot exceed total quantity")

        # Calculate remaining quantity if not provided
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity - self.filled_quantity

        return self

    def is_market_order(self) -> bool:
        """Check if this is a market order"""
        return self.order_type == "MARKET"

    def is_limit_order(self) -> bool:
        """Check if this is a limit order"""
        return self.order_type in ["LIMIT", "STOP_LIMIT"]

    def is_fully_filled(self) -> bool:
        """Check if order is fully filled"""
        return self.filled_quantity >= self.quantity

    def is_partially_filled(self) -> bool:
        """Check if order is partially filled"""
        return 0 < self.filled_quantity < self.quantity

    def is_unfilled(self) -> bool:
        """Check if order is unfilled"""
        return self.filled_quantity == 0

    def calculate_notional_value(self) -> Optional[float]:
        """Calculate notional value of the order"""
        if self.price is not None:
            return self.quantity * self.price
        return None

    def set_risk_check_result(self, result: Dict[str, Any]) -> None:
        """Set risk check result and update timestamp"""
        self.risk_check_result = result
        self.update_timestamp()

    def set_execution_data(self, execution_data: Dict[str, Any]) -> None:
        """Set execution data and update timestamp"""
        self.execution_data = execution_data
        self.update_timestamp()

    def update_fill(self, fill_quantity: int, fill_price: float) -> None:
        """Update order with fill information"""
        self.filled_quantity += fill_quantity
        self.remaining_quantity = self.quantity - self.filled_quantity

        # Update average fill price
        if self.average_fill_price is None:
            self.average_fill_price = fill_price
        else:
            total_filled_value = (
                self.filled_quantity - fill_quantity
            ) * self.average_fill_price + fill_quantity * fill_price
            self.average_fill_price = total_filled_value / self.filled_quantity

        self.update_timestamp()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        # Add state for API compatibility
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
