from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Portfolio(CyodaEntity):
    """
    Portfolio represents a trading account with positions, P&L, and risk metrics.
    Tracks positions, cash balance, margin, and portfolio performance.
    """

    ENTITY_NAME: ClassVar[str] = "Portfolio"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    account_name: str = Field(..., alias="accountName", description="Account name")
    positions: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of open positions"
    )
    cash_balance: float = Field(..., alias="cashBalance", description="Available cash")
    total_market_value: float = Field(
        ..., alias="totalMarketValue", description="Total market value"
    )
    total_cost_basis: float = Field(
        ..., alias="totalCostBasis", description="Total cost basis"
    )
    unrealized_pnl: float = Field(
        ..., alias="unrealizedPnl", description="Unrealized P&L"
    )
    unrealized_pnl_percent: float = Field(
        ..., alias="unrealizedPnlPercent", description="Unrealized P&L %"
    )
    realized_pnl: float = Field(
        default=0.0, alias="realizedPnl", description="Realized P&L"
    )
    total_pnl: float = Field(..., alias="totalPnl", description="Total P&L")
    total_pnl_percent: float = Field(
        ..., alias="totalPnlPercent", description="Total P&L %"
    )
    margin_used: float = Field(default=0.0, alias="marginUsed", description="Margin used")
    margin_available: float = Field(
        ..., alias="marginAvailable", description="Available margin"
    )
    margin_ratio: float = Field(default=0.0, alias="marginRatio", description="Margin ratio")
    buying_power: float = Field(..., alias="buyingPower", description="Buying power")
    last_updated: str = Field(..., alias="lastUpdated", description="Last update timestamp")
    currency: str = Field(default="USD", description="Currency")

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Account ID must be non-empty")
        return v.strip()

    @field_validator("cash_balance", "total_market_value", "buying_power")
    @classmethod
    def validate_amounts(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Amount cannot be negative")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

