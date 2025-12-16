from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Position represents a trading position for an account and symbol.
    
    Tracks current holdings, average entry price, and profit/loss metrics
    for risk management and reporting.
    """

    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., description="Account identifier")
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, BTC/USD)")
    quantity: float = Field(..., description="Current position quantity (positive for long, negative for short)")
    avg_price: float = Field(..., description="Average entry price")
    realized_pnl: float = Field(
        default=0.0,
        description="Realized profit/loss from closed positions"
    )
    unrealized_pnl: Optional[float] = Field(
        None,
        description="Unrealized profit/loss based on current market price"
    )

    @field_validator("avg_price")
    @classmethod
    def validate_avg_price(cls, v: float) -> float:
        """Validate average price is positive"""
        if v <= 0:
            raise ValueError("Average price must be positive")
        return v

    def get_notional_value(self, current_price: float) -> float:
        """Calculate current notional value of position"""
        return abs(self.quantity) * current_price

    def get_pnl_percentage(self, current_price: float) -> float:
        """Calculate P&L as percentage of entry value"""
        if self.quantity == 0:
            return 0.0
        entry_value = abs(self.quantity) * self.avg_price
        if entry_value == 0:
            return 0.0
        current_value = self.get_notional_value(current_price)
        pnl = current_value - entry_value
        if self.quantity < 0:
            pnl = -pnl
        return (pnl / entry_value) * 100

    def is_long(self) -> bool:
        """Check if position is long"""
        return self.quantity > 0

    def is_short(self) -> bool:
        """Check if position is short"""
        return self.quantity < 0

    def is_flat(self) -> bool:
        """Check if position is flat (no holdings)"""
        return self.quantity == 0

