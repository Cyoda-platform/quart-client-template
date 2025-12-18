"""
Account entity for trading platform.

Represents a trading account with portfolio aggregation, P&L tracking,
and multi-tenant separation.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Account(CyodaEntity):
    """
    Represents a trading account in the trading system.
    
    Manages account lifecycle: initial_state -> active -> suspended -> closed -> archived
    """

    ENTITY_NAME: ClassVar[str] = "Account"
    ENTITY_VERSION: ClassVar[int] = 1

    account_number: str = Field(
        ..., alias="accountNumber", description="Unique account number"
    )
    account_name: str = Field(
        ..., alias="accountName", description="Account display name"
    )
    account_type: str = Field(
        ..., alias="accountType", description="INDIVIDUAL, INSTITUTIONAL, PROP"
    )
    currency: str = Field(default="USD", description="Base currency")
    cash_balance: float = Field(
        default=0.0, alias="cashBalance", description="Available cash"
    )
    portfolio_value: float = Field(
        default=0.0, alias="portfolioValue", description="Total portfolio value"
    )
    total_equity: float = Field(
        default=0.0, alias="totalEquity", description="Cash + Portfolio Value"
    )
    buying_power: float = Field(
        default=0.0, alias="buyingPower", description="Available buying power"
    )
    margin_used: float = Field(
        default=0.0, alias="marginUsed", description="Margin currently used"
    )
    margin_available: float = Field(
        default=0.0, alias="marginAvailable", description="Available margin"
    )
    day_trading_buying_power: float = Field(
        default=0.0, alias="dayTradingBuyingPower", description="Day trading buying power"
    )
    is_active: bool = Field(
        default=True, alias="isActive", description="Whether account is active"
    )
    created_at: str = Field(..., alias="createdAt", description="Account creation time")
    updated_at: Optional[str] = Field(
        default=None, alias="updatedAt", description="Last update time"
    )

    def is_margin_call(self) -> bool:
        return self.margin_available <= 0

    def margin_utilization(self) -> float:
        if self.margin_used + self.margin_available == 0:
            return 0.0
        return self.margin_used / (self.margin_used + self.margin_available)

