"""
Portfolio entity for trading platform.

Represents aggregated portfolio metrics and holdings summary
for an account with real-time P&L calculations.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Portfolio(CyodaEntity):
    """
    Represents a portfolio in the trading system.
    
    Manages portfolio lifecycle: initial_state -> active -> archived
    """

    ENTITY_NAME: ClassVar[str] = "Portfolio"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    total_positions: int = Field(
        default=0, alias="totalPositions", description="Number of open positions"
    )
    total_market_value: float = Field(
        default=0.0, alias="totalMarketValue", description="Total market value of holdings"
    )
    total_cost_basis: float = Field(
        default=0.0, alias="totalCostBasis", description="Total cost basis"
    )
    total_unrealized_pnl: float = Field(
        default=0.0, alias="totalUnrealizedPnl", description="Total unrealized P&L"
    )
    total_realized_pnl: float = Field(
        default=0.0, alias="totalRealizedPnl", description="Total realized P&L"
    )
    total_pnl: float = Field(
        default=0.0, alias="totalPnl", description="Total P&L (realized + unrealized)"
    )
    total_pnl_percent: float = Field(
        default=0.0, alias="totalPnlPercent", description="Total P&L as percentage"
    )
    largest_position_symbol: Optional[str] = Field(
        default=None, alias="largestPositionSymbol", description="Symbol of largest position"
    )
    largest_position_value: float = Field(
        default=0.0, alias="largestPositionValue", description="Value of largest position"
    )
    concentration_percent: float = Field(
        default=0.0, alias="concentrationPercent", description="Largest position as % of portfolio"
    )
    updated_at: str = Field(..., alias="updatedAt", description="Last update time")

    def is_profitable(self) -> bool:
        return self.total_pnl > 0

    def is_concentrated(self) -> bool:
        return self.concentration_percent > 30.0

