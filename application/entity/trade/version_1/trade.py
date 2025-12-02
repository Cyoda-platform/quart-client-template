"""
Trade Entity for Real-Time Trading Platform

Represents executed transactions with settlement tracking and trade reporting
for regulatory compliance.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Trade(CyodaEntity):
    """
    Trade entity represents executed transactions with settlement tracking.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> validated -> settled -> reported
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Trade"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    trade_id: str = Field(
        ..., 
        alias="tradeId",
        description="Business trade identifier"
    )
    order_id: str = Field(
        ..., 
        alias="orderId",
        description="Originating order identifier"
    )
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="Trade side: BUY or SELL")
    quantity: int = Field(..., description="Executed quantity")
    price: float = Field(..., description="Execution price")
    portfolio_id: str = Field(
        ..., 
        alias="portfolioId",
        description="Associated portfolio identifier"
    )
    execution_time: str = Field(
        ..., 
        alias="executionTime",
        description="Execution timestamp (ISO 8601 format)"
    )
    settlement_date: str = Field(
        ..., 
        alias="settlementDate",
        description="Settlement date (ISO 8601 format)"
    )

    # Trade metadata
    exchange: Optional[str] = Field(
        default=None,
        description="Execution exchange"
    )
    counterparty: Optional[str] = Field(
        default=None,
        description="Trade counterparty"
    )
    commission: Optional[float] = Field(
        default=0.0,
        description="Commission charged"
    )
    fees: Optional[float] = Field(
        default=0.0,
        description="Additional fees"
    )

    # Settlement tracking
    settlement_status: str = Field(
        default="PENDING",
        alias="settlementStatus",
        description="Settlement status: PENDING, SETTLED, FAILED"
    )
    settlement_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="settlementData",
        description="Settlement processing data"
    )

    # Reporting fields
    reporting_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="reportingData",
        description="Regulatory reporting data"
    )

    # Validation constants
    ALLOWED_SIDES: ClassVar[List[str]] = ["BUY", "SELL"]
    ALLOWED_SETTLEMENT_STATUSES: ClassVar[List[str]] = ["PENDING", "SETTLED", "FAILED"]

    @field_validator("trade_id")
    @classmethod
    def validate_trade_id(cls, v: str) -> str:
        """Validate trade ID format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Trade ID must be non-empty")
        if len(v) > 50:
            raise ValueError("Trade ID must be at most 50 characters long")
        return v.strip()

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate trading symbol format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol must be non-empty")
        return v.strip().upper()

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate trade side"""
        if v not in cls.ALLOWED_SIDES:
            raise ValueError(f"Trade side must be one of: {cls.ALLOWED_SIDES}")
        return v

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        """Validate quantity is positive"""
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate price is positive"""
        if v <= 0:
            raise ValueError("Price must be positive")
        return v

    @field_validator("settlement_status")
    @classmethod
    def validate_settlement_status(cls, v: str) -> str:
        """Validate settlement status"""
        if v not in cls.ALLOWED_SETTLEMENT_STATUSES:
            raise ValueError(f"Settlement status must be one of: {cls.ALLOWED_SETTLEMENT_STATUSES}")
        return v

    def calculate_notional_value(self) -> float:
        """Calculate notional value of the trade"""
        return self.quantity * self.price

    def calculate_total_cost(self) -> float:
        """Calculate total cost including fees and commission"""
        notional = self.calculate_notional_value()
        total_fees = (self.commission or 0) + (self.fees or 0)
        
        if self.side == "BUY":
            return notional + total_fees
        else:  # SELL
            return notional - total_fees

    def is_settled(self) -> bool:
        """Check if trade is settled"""
        return self.settlement_status == "SETTLED"

    def set_settlement_data(self, settlement_data: Dict[str, Any]) -> None:
        """Set settlement data and update timestamp"""
        self.settlement_data = settlement_data
        self.update_timestamp()

    def set_reporting_data(self, reporting_data: Dict[str, Any]) -> None:
        """Set reporting data and update timestamp"""
        self.reporting_data = reporting_data
        self.update_timestamp()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        # Add state for API compatibility
        data["state"] = self.state
        # Add calculated fields
        data["notionalValue"] = self.calculate_notional_value()
        data["totalCost"] = self.calculate_total_cost()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
