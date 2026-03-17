"""
Position entity for institutional trading platform.

Manages real-time positions per instrument, account, and legal entity.
Tracks holdings, average price, realized/unrealized P&L in real-time.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Position represents a real-time position in the institutional trading system.
    
    Tracks holdings, average price, and P&L calculations per instrument and account.
    States: open -> closed
    """

    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    # Position identification
    position_id: str = Field(..., alias="positionId", description="Unique position identifier")
    
    # Instrument and account
    symbol: str = Field(..., description="Trading symbol")
    account_id: str = Field(..., alias="accountId", description="Trading account ID")
    legal_entity: str = Field(..., alias="legalEntity", description="Legal entity code")
    
    # Position details
    quantity: float = Field(..., description="Current position quantity")
    average_cost: float = Field(..., alias="averageCost", description="Average cost per unit")
    current_price: Optional[float] = Field(
        default=None, alias="currentPrice", description="Current market price"
    )
    
    # P&L calculations
    unrealized_pnl: Optional[float] = Field(
        default=None, alias="unrealizedPnl", description="Unrealized P&L"
    )
    realized_pnl: Optional[float] = Field(
        default=None, alias="realizedPnl", description="Realized P&L"
    )
    total_pnl: Optional[float] = Field(
        default=None, alias="totalPnl", description="Total P&L (realized + unrealized)"
    )
    
    # Risk metrics
    notional_value: Optional[float] = Field(
        default=None, alias="notionalValue", description="Notional position value"
    )
    margin_requirement: Optional[float] = Field(
        default=None, alias="marginRequirement", description="Margin requirement"
    )
    
    # Timestamps
    opened_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="openedAt",
        description="Position open timestamp",
    )
    closed_at: Optional[str] = Field(
        default=None, alias="closedAt", description="Position close timestamp"
    )
    last_updated_at: Optional[str] = Field(
        default=None, alias="lastUpdatedAt", description="Last update timestamp"
    )

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        """Validate quantity (can be negative for short positions)"""
        return v

    @field_validator("average_cost")
    @classmethod
    def validate_average_cost(cls, v: float) -> float:
        """Validate average cost is non-negative"""
        if v < 0:
            raise ValueError("Average cost must be non-negative")
        return v

    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L"""
        return self.quantity * (current_price - self.average_cost)

    def calculate_notional_value(self, current_price: float) -> float:
        """Calculate notional position value"""
        return abs(self.quantity * current_price)

    def is_long(self) -> bool:
        """Check if position is long"""
        return self.quantity > 0

    def is_short(self) -> bool:
        """Check if position is short"""
        return self.quantity < 0

    def is_flat(self) -> bool:
        """Check if position is flat (closed)"""
        return self.quantity == 0

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

