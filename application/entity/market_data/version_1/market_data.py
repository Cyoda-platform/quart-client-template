from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class MarketData(CyodaEntity):
    """
    MarketData represents real-time market data for a trading symbol.
    Manages low-latency ingestion, normalization, and snapshot storage.
    """

    ENTITY_NAME: ClassVar[str] = "MarketData"
    ENTITY_VERSION: ClassVar[int] = 1

    symbol: str = Field(..., description="Trading symbol (e.g., AAPL)")
    timestamp: str = Field(..., description="Data timestamp in ISO 8601 format")
    bid: float = Field(..., description="Current bid price")
    ask: float = Field(..., description="Current ask price")
    last: float = Field(..., description="Last traded price")
    volume: int = Field(..., description="Current volume")
    source: str = Field(..., description="Data source (NASDAQ, NYSE, etc.)")
    bid_size: Optional[int] = Field(
        default=None, alias="bidSize", description="Bid size in shares"
    )
    ask_size: Optional[int] = Field(
        default=None, alias="askSize", description="Ask size in shares"
    )
    open_price: Optional[float] = Field(
        default=None, alias="open", description="Opening price"
    )
    high: Optional[float] = Field(default=None, description="Day high price")
    low: Optional[float] = Field(default=None, description="Day low price")
    close: Optional[float] = Field(default=None, description="Closing price")
    vwap: Optional[float] = Field(
        default=None, description="Volume weighted average price"
    )
    change: Optional[float] = Field(default=None, description="Price change")
    change_percent: Optional[float] = Field(
        default=None, alias="changePercent", description="Percentage change"
    )
    day_volume: Optional[int] = Field(
        default=None, alias="dayVolume", description="Total day volume"
    )
    exchange_status: Optional[str] = Field(
        default=None, alias="exchangeStatus", description="Exchange status"
    )
    data_quality: Optional[str] = Field(
        default=None, alias="dataQuality", description="Data quality indicator"
    )

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol must be non-empty")
        if len(v) > 10:
            raise ValueError("Symbol must be at most 10 characters")
        return v.upper().strip()

    @field_validator("bid", "ask", "last")
    @classmethod
    def validate_prices(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Volume cannot be negative")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
