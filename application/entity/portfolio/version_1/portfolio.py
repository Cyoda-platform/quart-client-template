from datetime import datetime, timezone
from typing import ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class Portfolio(CyodaEntity):
    """
    Portfolio aggregates positions and tracks overall portfolio metrics.

    Provides comprehensive portfolio-level risk and performance analytics.
    States: initial_state -> created -> active -> rebalancing -> completed
    """

    ENTITY_NAME: ClassVar[str] = "Portfolio"
    ENTITY_VERSION: ClassVar[int] = 1

    # Portfolio identification
    portfolio_id: str = Field(..., description="Unique portfolio identifier")
    account_id: str = Field(..., description="Trading account ID")
    portfolio_name: str = Field(..., description="Portfolio name")

    # Portfolio values
    total_value: float = Field(..., ge=0, description="Total portfolio value")
    cash_balance: float = Field(..., description="Available cash")
    buying_power: float = Field(..., ge=0, description="Available buying power")

    # Performance metrics
    total_pnl: float = Field(default=0, description="Total P&L")
    unrealized_pnl: float = Field(default=0, description="Unrealized P&L")
    realized_pnl: float = Field(default=0, description="Realized P&L")
    pnl_percentage: float = Field(default=0, description="P&L as percentage")

    # Risk metrics
    portfolio_delta: float = Field(default=0, description="Portfolio delta")
    portfolio_gamma: float = Field(default=0, description="Portfolio gamma")
    portfolio_vega: float = Field(default=0, description="Portfolio vega")
    portfolio_theta: float = Field(default=0, description="Portfolio theta")
    var_95: Optional[float] = Field(None, description="Value at Risk 95%")

    # Position tracking
    position_count: int = Field(default=0, ge=0, description="Number of open positions")
    sector_allocation: Optional[Dict[str, float]] = Field(
        None, description="Sector allocation"
    )

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
    )
    updated_at: Optional[str] = Field(None, alias="updatedAt")
    last_rebalance: Optional[str] = Field(None, alias="lastRebalance")

    @field_validator("portfolio_name")
    @classmethod
    def validate_portfolio_name(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Portfolio name must be non-empty")
        if len(v) > 100:
            raise ValueError("Portfolio name must be at most 100 characters")
        return v.strip()

    @model_validator(mode="after")
    def validate_portfolio_logic(self) -> "Portfolio":
        if self.total_value < 0:
            raise ValueError("Total value cannot be negative")
        if self.position_count < 0:
            raise ValueError("Position count cannot be negative")
        return self

    def update_metrics(
        self, total_value: float, unrealized_pnl: float, realized_pnl: float
    ) -> None:
        self.total_value = total_value
        self.unrealized_pnl = unrealized_pnl
        self.realized_pnl = realized_pnl
        self.total_pnl = unrealized_pnl + realized_pnl
        if total_value > 0:
            self.pnl_percentage = (self.total_pnl / total_value) * 100
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def get_leverage_ratio(self) -> float:
        if self.total_value == 0:
            return 0.0
        return self.total_value / (self.total_value - abs(self.cash_balance))

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
