"""
MarketData entity for institutional trading platform.

Manages real-time market data feeds (Level 1 & 2) with nanosecond precision timestamps.
Supports multiple EU venues (LSE, Euronext, XETRA).
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class MarketData(CyodaEntity):
    """
    MarketData represents real-time market data in the trading system.

    Supports Level 1 (top of book) and Level 2 (order book depth) data.
    States: active -> inactive
    """

    ENTITY_NAME: ClassVar[str] = "MarketData"
    ENTITY_VERSION: ClassVar[int] = 1

    # Market data identification
    market_data_id: str = Field(
        ..., alias="marketDataId", description="Unique market data identifier"
    )
    symbol: str = Field(..., description="Trading symbol")
    venue: str = Field(..., description="Data source venue (LSE, Euronext, XETRA)")

    # Level 1 data (top of book)
    bid_price: Optional[float] = Field(
        default=None, alias="bidPrice", description="Best bid price"
    )
    bid_size: Optional[float] = Field(
        default=None, alias="bidSize", description="Best bid size"
    )
    ask_price: Optional[float] = Field(
        default=None, alias="askPrice", description="Best ask price"
    )
    ask_size: Optional[float] = Field(
        default=None, alias="askSize", description="Best ask size"
    )
    last_price: Optional[float] = Field(
        default=None, alias="lastPrice", description="Last traded price"
    )
    last_size: Optional[float] = Field(
        default=None, alias="lastSize", description="Last traded size"
    )

    # Level 2 data (order book depth)
    bid_levels: Optional[str] = Field(
        default=None, alias="bidLevels", description="Bid levels (JSON array)"
    )
    ask_levels: Optional[str] = Field(
        default=None, alias="askLevels", description="Ask levels (JSON array)"
    )

    # Market statistics
    open_price: Optional[float] = Field(
        default=None, alias="openPrice", description="Opening price"
    )
    high_price: Optional[float] = Field(
        default=None, alias="highPrice", description="High price"
    )
    low_price: Optional[float] = Field(
        default=None, alias="lowPrice", description="Low price"
    )
    close_price: Optional[float] = Field(
        default=None, alias="closePrice", description="Closing price"
    )
    volume: Optional[float] = Field(default=None, description="Trading volume")

    # Timestamps (nanosecond precision)
    exchange_timestamp: Optional[str] = Field(
        default=None,
        alias="exchangeTimestamp",
        description="Exchange timestamp (nanosecond precision)",
    )
    received_timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="receivedTimestamp",
        description="Data received timestamp",
    )

    # Data quality
    is_stale: bool = Field(
        default=False, alias="isStale", description="Whether data is stale"
    )
    feed_status: str = Field(
        default="active",
        alias="feedStatus",
        description="Feed status: active, inactive, halted",
    )

    @field_validator("bid_price", "ask_price", "last_price")
    @classmethod
    def validate_prices(cls, v: Optional[float]) -> Optional[float]:
        """Validate prices are positive"""
        if v is not None and v <= 0:
            raise ValueError("Price must be positive")
        return v

    @field_validator("bid_size", "ask_size", "last_size", "volume")
    @classmethod
    def validate_sizes(cls, v: Optional[float]) -> Optional[float]:
        """Validate sizes are non-negative"""
        if v is not None and v < 0:
            raise ValueError("Size must be non-negative")
        return v

    def get_spread(self) -> Optional[float]:
        """Calculate bid-ask spread"""
        if self.bid_price and self.ask_price:
            return self.ask_price - self.bid_price
        return None

    def get_mid_price(self) -> Optional[float]:
        """Calculate mid price"""
        if self.bid_price and self.ask_price:
            return (self.bid_price + self.ask_price) / 2
        return None

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
