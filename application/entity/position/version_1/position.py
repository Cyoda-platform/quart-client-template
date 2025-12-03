# entity/position/version_1/position.py

"""
Position Entity for Trading Platform

Represents current holdings and positions per instrument and client.
Manages position tracking, P&L calculation, and mark-to-market updates.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional
from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Position represents current holdings and positions per instrument and client
    with real-time P&L tracking and mark-to-market updates.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core identification
    client_id: str = Field(..., alias="clientId", description="Client identifier")
    instrument_id: str = Field(..., alias="instrumentId", description="Instrument technical ID")
    symbol: str = Field(..., description="Trading symbol")
    portfolio_id: Optional[str] = Field(default=None, alias="portfolioId", description="Portfolio technical ID")

    # Position details
    quantity: Decimal = Field(..., description="Position quantity (positive for long, negative for short)")
    average_price: Decimal = Field(..., alias="averagePrice", description="Average cost price")
    market_price: Optional[Decimal] = Field(default=None, alias="marketPrice", description="Current market price")
    
    # Valuation
    cost_basis: Decimal = Field(..., alias="costBasis", description="Total cost basis")
    market_value: Optional[Decimal] = Field(default=None, alias="marketValue", description="Current market value")
    unrealized_pnl: Optional[Decimal] = Field(default=None, alias="unrealizedPnl", description="Unrealized P&L")
    realized_pnl: Decimal = Field(default=Decimal("0"), alias="realizedPnl", description="Realized P&L")

    # Risk metrics
    delta: Optional[Decimal] = Field(default=None, description="Position delta")
    gamma: Optional[Decimal] = Field(default=None, description="Position gamma")
    theta: Optional[Decimal] = Field(default=None, description="Position theta")
    vega: Optional[Decimal] = Field(default=None, description="Position vega")

    # Timestamps
    opened_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="openedAt",
        description="Position opening timestamp"
    )
    last_updated: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="lastUpdated",
        description="Last update timestamp"
    )
    closed_at: Optional[str] = Field(default=None, alias="closedAt", description="Position closing timestamp")

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        """Validate client ID"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Client ID must be non-empty")
        return v.strip()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: Decimal) -> Decimal:
        """Validate quantity (can be negative for short positions)"""
        if v == 0:
            raise ValueError("Quantity cannot be zero")
        return v

    @field_validator("average_price")
    @classmethod
    def validate_average_price(cls, v: Decimal) -> Decimal:
        """Validate average price"""
        if v <= 0:
            raise ValueError("Average price must be positive")
        return v

    def __init__(self, **data):
        super().__init__(**data)
        # Calculate cost basis if not provided
        if "cost_basis" not in data:
            self.cost_basis = abs(self.quantity) * self.average_price

    def update_market_price(self, market_price: Decimal) -> None:
        """Update market price and recalculate P&L"""
        self.market_price = market_price
        self.market_value = self.quantity * market_price
        self.unrealized_pnl = self.market_value - (self.quantity * self.average_price)
        self.update_timestamp()

    def add_trade(self, trade_quantity: Decimal, trade_price: Decimal) -> None:
        """Add a trade to the position"""
        if (self.quantity > 0 and trade_quantity > 0) or (self.quantity < 0 and trade_quantity < 0):
            # Same direction - update average price
            total_cost = self.cost_basis + (abs(trade_quantity) * trade_price)
            total_quantity = abs(self.quantity) + abs(trade_quantity)
            self.average_price = total_cost / total_quantity
            self.quantity += trade_quantity
            self.cost_basis = abs(self.quantity) * self.average_price
        else:
            # Opposite direction - realize P&L
            if abs(trade_quantity) >= abs(self.quantity):
                # Close position completely
                self.realized_pnl += (trade_price - self.average_price) * abs(self.quantity)
                remaining_quantity = abs(trade_quantity) - abs(self.quantity)
                if remaining_quantity > 0:
                    # Open new position in opposite direction
                    self.quantity = remaining_quantity if trade_quantity > 0 else -remaining_quantity
                    self.average_price = trade_price
                    self.cost_basis = remaining_quantity * trade_price
                else:
                    # Position closed
                    self.quantity = Decimal("0")
                    self.cost_basis = Decimal("0")
                    self.closed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            else:
                # Partial close
                self.realized_pnl += (trade_price - self.average_price) * abs(trade_quantity)
                self.quantity += trade_quantity
                self.cost_basis = abs(self.quantity) * self.average_price
        
        self.update_timestamp()

    def update_greeks(self, delta: Optional[Decimal] = None, gamma: Optional[Decimal] = None,
                     theta: Optional[Decimal] = None, vega: Optional[Decimal] = None) -> None:
        """Update option Greeks"""
        if delta is not None:
            self.delta = delta
        if gamma is not None:
            self.gamma = gamma
        if theta is not None:
            self.theta = theta
        if vega is not None:
            self.vega = vega
        self.update_timestamp()

    def update_timestamp(self) -> None:
        """Update the last_updated timestamp"""
        self.last_updated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def is_long(self) -> bool:
        """Check if position is long"""
        return self.quantity > 0

    def is_short(self) -> bool:
        """Check if position is short"""
        return self.quantity < 0

    def is_closed(self) -> bool:
        """Check if position is closed"""
        return self.quantity == 0

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        data["isLong"] = self.is_long()
        data["isShort"] = self.is_short()
        data["isClosed"] = self.is_closed()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
