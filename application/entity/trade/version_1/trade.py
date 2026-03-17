"""
Trade entity for institutional trading platform.

Manages trade lifecycle: captured -> enriched -> reported
Includes trade enrichment with venue, execution algo, latency metrics, and counterparty.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Trade(CyodaEntity):
    """
    Trade represents an executed trade in the institutional trading system.

    Manages trade lifecycle with states: captured -> enriched -> reported.
    Includes enrichment with venue, execution algo, latency metrics, and counterparty.
    """

    ENTITY_NAME: ClassVar[str] = "Trade"
    ENTITY_VERSION: ClassVar[int] = 1

    # Trade identification
    trade_id: str = Field(..., alias="tradeId", description="Unique trade identifier")
    order_id: str = Field(..., alias="orderId", description="Related order ID")

    # Instrument and parties
    symbol: str = Field(..., description="Trading symbol")
    account_id: str = Field(..., alias="accountId", description="Trading account ID")
    legal_entity: str = Field(..., alias="legalEntity", description="Legal entity code")
    counterparty: Optional[str] = Field(
        default=None, description="Counterparty identifier"
    )

    # Trade details
    side: str = Field(..., description="Trade side: BUY or SELL")
    quantity: float = Field(..., description="Trade quantity")
    price: float = Field(..., description="Execution price")
    commission: Optional[float] = Field(default=None, description="Commission paid")

    # Execution details
    venue: str = Field(..., description="Execution venue (LSE, Euronext, XETRA, etc.)")
    execution_algo: Optional[str] = Field(
        default=None, alias="executionAlgo", description="Execution algorithm used"
    )
    execution_time: Optional[str] = Field(
        default=None,
        alias="executionTime",
        description="Execution timestamp (nanosecond precision)",
    )

    # Latency metrics
    order_to_execution_latency_us: Optional[float] = Field(
        default=None,
        alias="orderToExecutionLatencyUs",
        description="Latency in microseconds",
    )
    market_data_latency_us: Optional[float] = Field(
        default=None,
        alias="marketDataLatencyUs",
        description="Market data latency in microseconds",
    )

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Trade capture timestamp",
    )
    enriched_at: Optional[str] = Field(
        default=None, alias="enrichedAt", description="Trade enrichment timestamp"
    )
    reported_at: Optional[str] = Field(
        default=None, alias="reportedAt", description="Trade reporting timestamp"
    )

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        """Validate trade side"""
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

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Validate price is positive"""
        if v <= 0:
            raise ValueError("Price must be positive")
        return v

    def calculate_gross_value(self) -> float:
        """Calculate gross trade value"""
        return self.quantity * self.price

    def calculate_net_value(self) -> float:
        """Calculate net trade value after commission"""
        gross = self.calculate_gross_value()
        commission = self.commission or 0.0
        return gross - commission if self.side == "BUY" else gross + commission

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
