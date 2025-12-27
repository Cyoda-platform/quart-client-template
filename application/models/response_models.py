from typing import Optional

from pydantic import BaseModel, Field


class MarketDataResponse(BaseModel):
    """Response model for market data."""

    entity_id: Optional[str] = Field(default=None, alias="entityId")
    symbol: str
    timestamp: str
    bid: float
    ask: float
    last: float
    volume: int
    source: str
    state: Optional[str] = None


class OrderResponse(BaseModel):
    """Response model for orders."""

    entity_id: Optional[str] = Field(default=None, alias="entityId")
    order_id: str = Field(..., alias="orderId")
    account_id: str = Field(..., alias="accountId")
    symbol: str
    side: str
    order_type: str = Field(..., alias="orderType")
    quantity: int
    price: float
    status: str
    state: Optional[str] = None


class PortfolioResponse(BaseModel):
    """Response model for portfolios."""

    entity_id: Optional[str] = Field(default=None, alias="entityId")
    account_id: str = Field(..., alias="accountId")
    account_name: str = Field(..., alias="accountName")
    cash_balance: float = Field(..., alias="cashBalance")
    total_market_value: float = Field(..., alias="totalMarketValue")
    total_pnl: float = Field(..., alias="totalPnl")
    state: Optional[str] = None


class RiskResponse(BaseModel):
    """Response model for risk controls."""

    entity_id: Optional[str] = Field(default=None, alias="entityId")
    account_id: str = Field(..., alias="accountId")
    symbol: str
    position_limit: float = Field(..., alias="positionLimit")
    current_position: float = Field(..., alias="currentPosition")
    risk_level: str = Field(..., alias="riskLevel")
    is_alert_triggered: bool = Field(..., alias="isAlertTriggered")
    state: Optional[str] = None


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    code: Optional[str] = None


class DeleteResponse(BaseModel):
    """Response model for delete operations."""

    success: bool
    message: str
    entity_id: Optional[str] = Field(default=None, alias="entityId")
