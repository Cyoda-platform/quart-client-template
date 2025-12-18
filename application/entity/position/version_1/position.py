"""
Position entity for trading platform.

Represents current holdings and P&L for an account/symbol combination
with real-time updates from trade capture.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Represents a position (holding) in the trading system.
    
    Manages position lifecycle: initial_state -> open -> closed -> archived
    """

    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    symbol: str = Field(..., description="Instrument symbol")
    quantity: float = Field(..., description="Current quantity held")
    avg_cost: float = Field(..., alias="avgCost", description="Average cost per unit")
    market_price: float = Field(
        ..., alias="marketPrice", description="Current market price"
    )
    market_value: float = Field(
        ..., alias="marketValue", description="Quantity * Market Price"
    )
    unrealized_pnl: float = Field(
        ..., alias="unrealizedPnl", description="Unrealized P&L"
    )
    realized_pnl: float = Field(
        default=0.0, alias="realizedPnl", description="Realized P&L"
    )
    total_pnl: float = Field(
        ..., alias="totalPnl", description="Unrealized + Realized P&L"
    )
    pnl_percent: float = Field(
        ..., alias="pnlPercent", description="P&L as percentage"
    )
    last_trade_time: Optional[str] = Field(
        default=None, alias="lastTradeTime", description="Last trade timestamp"
    )
    updated_at: str = Field(..., alias="updatedAt", description="Last update time")

    def is_long(self) -> bool:
        return self.quantity > 0

    def is_short(self) -> bool:
        return self.quantity < 0

    def is_flat(self) -> bool:
        return self.quantity == 0

