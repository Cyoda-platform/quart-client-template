# entity/order/version_1/order.py

"""
Order Entity for Trading Platform

Represents trading orders with complete lifecycle management including validation,
risk checking, compliance approval, execution, and settlement.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional
from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order represents a trading order with complete lifecycle management
    from submission through execution and settlement.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core order fields
    order_id: str = Field(..., alias="orderId", description="Unique order identifier")
    client_id: str = Field(..., alias="clientId", description="Client identifier")
    instrument_id: str = Field(..., alias="instrumentId", description="Instrument technical ID")
    symbol: str = Field(..., description="Trading symbol")

    # Order specifications
    side: str = Field(..., description="Order side (BUY, SELL)")
    quantity: Decimal = Field(..., description="Order quantity")
    price: Optional[Decimal] = Field(default=None, description="Order price (null for market orders)")
    order_type: str = Field(..., alias="orderType", description="Order type (MARKET, LIMIT, STOP)")
    time_in_force: str = Field(default="DAY", alias="timeInForce", description="Time in force (DAY, GTC, IOC, FOK)")

    # Execution details
    filled_quantity: Decimal = Field(default=Decimal("0"), alias="filledQuantity", description="Quantity filled")
    remaining_quantity: Decimal = Field(default=None, alias="remainingQuantity", description="Quantity remaining")
    average_price: Optional[Decimal] = Field(default=None, alias="averagePrice", description="Average execution price")
    
    # Status and tracking
    order_status: str = Field(default="PENDING", alias="orderStatus", description="Current order status")
    rejection_reason: Optional[str] = Field(default=None, alias="rejectionReason", description="Reason for rejection")
    
    # Risk and compliance
    risk_checked: bool = Field(default=False, alias="riskChecked", description="Whether risk checks passed")
    compliance_approved: bool = Field(default=False, alias="complianceApproved", description="Whether compliance approved")
    
    # Timestamps
    submitted_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="submittedAt",
        description="Order submission timestamp"
    )
    executed_at: Optional[str] = Field(default=None, alias="executedAt", description="Order execution timestamp")
    settled_at: Optional[str] = Field(default=None, alias="settledAt", description="Order settlement timestamp")

    # Validation constants
    VALID_SIDES: ClassVar[List[str]] = ["BUY", "SELL"]
    VALID_ORDER_TYPES: ClassVar[List[str]] = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]
    VALID_TIME_IN_FORCE: ClassVar[List[str]] = ["DAY", "GTC", "IOC", "FOK"]
    VALID_ORDER_STATUSES: ClassVar[List[str]] = ["PENDING", "VALIDATED", "RISK_CHECKED", "COMPLIANCE_APPROVED", "EXECUTED", "SETTLED", "REJECTED", "CANCELLED"]

    @field_validator("order_id")
    @classmethod
    def validate_order_id(cls, v: str) -> str:
        """Validate order ID format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Order ID must be non-empty")
        return v.strip()

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate order side"""
        if v not in cls.VALID_SIDES:
            raise ValueError(f"Side must be one of: {cls.VALID_SIDES}")
        return v

    @field_validator("order_type")
    @classmethod
    def validate_order_type(cls, v: str) -> str:
        """Validate order type"""
        if v not in cls.VALID_ORDER_TYPES:
            raise ValueError(f"Order type must be one of: {cls.VALID_ORDER_TYPES}")
        return v

    @field_validator("time_in_force")
    @classmethod
    def validate_time_in_force(cls, v: str) -> str:
        """Validate time in force"""
        if v not in cls.VALID_TIME_IN_FORCE:
            raise ValueError(f"Time in force must be one of: {cls.VALID_TIME_IN_FORCE}")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        """Validate order quantity"""
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    def __init__(self, **data):
        super().__init__(**data)
        if self.remaining_quantity is None:
            self.remaining_quantity = self.quantity

    def update_execution(self, fill_quantity: Decimal, fill_price: Decimal) -> None:
        """Update order with execution details"""
        self.filled_quantity += fill_quantity
        self.remaining_quantity = self.quantity - self.filled_quantity
        
        # Calculate average price
        if self.average_price is None:
            self.average_price = fill_price
        else:
            total_value = (self.filled_quantity - fill_quantity) * self.average_price + fill_quantity * fill_price
            self.average_price = total_value / self.filled_quantity
        
        if self.remaining_quantity == 0:
            self.order_status = "FILLED"
        else:
            self.order_status = "PARTIALLY_FILLED"
        
        if self.executed_at is None:
            self.executed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def reject_order(self, reason: str) -> None:
        """Reject the order with reason"""
        self.order_status = "REJECTED"
        self.rejection_reason = reason

    def cancel_order(self) -> None:
        """Cancel the order"""
        self.order_status = "CANCELLED"

    def is_executable(self) -> bool:
        """Check if order is ready for execution"""
        return (self.risk_checked and 
                self.compliance_approved and 
                self.order_status == "COMPLIANCE_APPROVED")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
