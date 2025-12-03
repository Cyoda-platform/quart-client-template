# entity/portfolio/version_1/portfolio.py

"""
Portfolio Entity for Trading Platform

Represents aggregated portfolio view and performance tracking for clients.
Manages portfolio valuation, P&L calculation, and risk metrics.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional
from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Portfolio(CyodaEntity):
    """
    Portfolio represents aggregated portfolio view and performance tracking
    for a client including positions, cash, and risk metrics.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Portfolio"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core identification
    client_id: str = Field(..., alias="clientId", description="Client identifier")
    portfolio_name: str = Field(..., alias="portfolioName", description="Portfolio name")
    base_currency: str = Field(default="USD", alias="baseCurrency", description="Base currency for portfolio")

    # Financial metrics
    total_value: Decimal = Field(default=Decimal("0"), alias="totalValue", description="Total portfolio value")
    cash_balance: Decimal = Field(default=Decimal("0"), alias="cashBalance", description="Cash balance")
    invested_value: Decimal = Field(default=Decimal("0"), alias="investedValue", description="Total invested value")
    market_value: Decimal = Field(default=Decimal("0"), alias="marketValue", description="Current market value of positions")

    # P&L metrics
    daily_pnl: Decimal = Field(default=Decimal("0"), alias="dailyPnl", description="Daily profit and loss")
    total_pnl: Decimal = Field(default=Decimal("0"), alias="totalPnl", description="Total profit and loss")
    unrealized_pnl: Decimal = Field(default=Decimal("0"), alias="unrealizedPnl", description="Unrealized profit and loss")
    realized_pnl: Decimal = Field(default=Decimal("0"), alias="realizedPnl", description="Realized profit and loss")

    # Risk metrics
    var_95: Optional[Decimal] = Field(default=None, alias="var95", description="Value at Risk 95%")
    beta: Optional[Decimal] = Field(default=None, description="Portfolio beta")
    sharpe_ratio: Optional[Decimal] = Field(default=None, alias="sharpeRatio", description="Sharpe ratio")
    max_drawdown: Optional[Decimal] = Field(default=None, alias="maxDrawdown", description="Maximum drawdown")

    # Position summary
    position_count: int = Field(default=0, alias="positionCount", description="Number of positions")
    long_positions: int = Field(default=0, alias="longPositions", description="Number of long positions")
    short_positions: int = Field(default=0, alias="shortPositions", description="Number of short positions")

    # Performance tracking
    inception_date: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="inceptionDate",
        description="Portfolio inception date"
    )
    last_updated: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="lastUpdated",
        description="Last portfolio update timestamp"
    )

    # Status
    is_active: bool = Field(default=True, alias="isActive", description="Whether portfolio is active")

    @field_validator("client_id")
    @classmethod
    def validate_client_id(cls, v: str) -> str:
        """Validate client ID"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Client ID must be non-empty")
        return v.strip()

    @field_validator("portfolio_name")
    @classmethod
    def validate_portfolio_name(cls, v: str) -> str:
        """Validate portfolio name"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Portfolio name must be non-empty")
        if len(v) > 100:
            raise ValueError("Portfolio name must be at most 100 characters")
        return v.strip()

    @field_validator("base_currency")
    @classmethod
    def validate_base_currency(cls, v: str) -> str:
        """Validate base currency"""
        valid_currencies = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"]
        if v not in valid_currencies:
            raise ValueError(f"Base currency must be one of: {valid_currencies}")
        return v

    def update_portfolio_value(self, cash_balance: Decimal, market_value: Decimal) -> None:
        """Update portfolio value calculations"""
        self.cash_balance = cash_balance
        self.market_value = market_value
        self.total_value = cash_balance + market_value
        self.update_timestamp()

    def update_pnl(self, daily_pnl: Decimal, unrealized_pnl: Decimal, realized_pnl: Decimal) -> None:
        """Update P&L metrics"""
        self.daily_pnl = daily_pnl
        self.unrealized_pnl = unrealized_pnl
        self.realized_pnl = realized_pnl
        self.total_pnl = unrealized_pnl + realized_pnl
        self.update_timestamp()

    def update_risk_metrics(self, var_95: Optional[Decimal] = None, 
                           beta: Optional[Decimal] = None,
                           sharpe_ratio: Optional[Decimal] = None,
                           max_drawdown: Optional[Decimal] = None) -> None:
        """Update risk metrics"""
        if var_95 is not None:
            self.var_95 = var_95
        if beta is not None:
            self.beta = beta
        if sharpe_ratio is not None:
            self.sharpe_ratio = sharpe_ratio
        if max_drawdown is not None:
            self.max_drawdown = max_drawdown
        self.update_timestamp()

    def update_position_summary(self, position_count: int, long_positions: int, short_positions: int) -> None:
        """Update position summary"""
        self.position_count = position_count
        self.long_positions = long_positions
        self.short_positions = short_positions
        self.update_timestamp()

    def update_timestamp(self) -> None:
        """Update the last_updated timestamp"""
        self.last_updated = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def calculate_return_percentage(self) -> Optional[Decimal]:
        """Calculate portfolio return percentage"""
        if self.invested_value > 0:
            return (self.total_pnl / self.invested_value) * 100
        return None

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        data["returnPercentage"] = self.calculate_return_percentage()
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
