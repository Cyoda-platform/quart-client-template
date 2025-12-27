from typing import Optional

from pydantic import BaseModel, Field


class MarketDataRequest(BaseModel):
    """Request model for creating/updating market data."""

    symbol: str = Field(..., description="Trading symbol")
    timestamp: str = Field(..., description="Data timestamp")
    bid: float = Field(..., description="Bid price")
    ask: float = Field(..., description="Ask price")
    last: float = Field(..., description="Last price")
    volume: int = Field(..., description="Volume")
    source: str = Field(..., description="Data source")
    bid_size: Optional[int] = Field(default=None, alias="bidSize")
    ask_size: Optional[int] = Field(default=None, alias="askSize")


class OrderRequest(BaseModel):
    """Request model for creating/updating orders."""

    order_id: str = Field(..., alias="orderId")
    account_id: str = Field(..., alias="accountId")
    symbol: str
    side: str
    order_type: str = Field(..., alias="orderType")
    quantity: int
    price: float
    status: str
    created_at: str = Field(..., alias="createdAt")
    order_value: float = Field(..., alias="orderValue")
    total_cost: float = Field(..., alias="totalCost")


class PortfolioRequest(BaseModel):
    """Request model for creating/updating portfolios."""

    account_id: str = Field(..., alias="accountId")
    account_name: str = Field(..., alias="accountName")
    cash_balance: float = Field(..., alias="cashBalance")
    total_market_value: float = Field(..., alias="totalMarketValue")
    total_cost_basis: float = Field(..., alias="totalCostBasis")
    unrealized_pnl: float = Field(..., alias="unrealizedPnl")
    unrealized_pnl_percent: float = Field(..., alias="unrealizedPnlPercent")
    total_pnl: float = Field(..., alias="totalPnl")
    total_pnl_percent: float = Field(..., alias="totalPnlPercent")
    margin_available: float = Field(..., alias="marginAvailable")
    buying_power: float = Field(..., alias="buyingPower")
    last_updated: str = Field(..., alias="lastUpdated")


class RiskRequest(BaseModel):
    """Request model for creating/updating risk controls."""

    account_id: str = Field(..., alias="accountId")
    symbol: str
    position_limit: float = Field(..., alias="positionLimit")
    current_position: float = Field(..., alias="currentPosition")
    notional_limit: float = Field(..., alias="notionalLimit")
    current_notional: float = Field(..., alias="currentNotional")
    margin_requirement: float = Field(..., alias="marginRequirement")
    margin_utilization: float = Field(..., alias="marginUtilization")
    last_checked: str = Field(..., alias="lastChecked")
