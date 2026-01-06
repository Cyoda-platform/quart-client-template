from datetime import datetime, timezone
from typing import ClassVar, List, Optional

from pydantic import ConfigDict, Field, field_validator, model_validator

from common.entity.cyoda_entity import CyodaEntity


class MarketData(CyodaEntity):
    """
    MarketData represents real-time market data feeds.

    Ingests and manages market data from various sources.
    States: initial_state -> created -> active -> archived -> completed
    """

    ENTITY_NAME: ClassVar[str] = "MarketData"
    ENTITY_VERSION: ClassVar[int] = 1

    # Market data identification
    symbol: str = Field(..., description="Trading symbol")
    data_source: str = Field(..., description="Data source (e.g., Bloomberg, Reuters)")
    feed_type: str = Field(..., description="QUOTE, TRADE, DEPTH, VOLATILITY")

    # Price data
    bid_price: float = Field(..., ge=0, description="Current bid price")
    ask_price: float = Field(..., ge=0, description="Current ask price")
    last_price: float = Field(..., ge=0, description="Last trade price")
    open_price: float = Field(..., ge=0, description="Opening price")
    high_price: float = Field(..., ge=0, description="High price")
    low_price: float = Field(..., ge=0, description="Low price")
    close_price: Optional[float] = Field(None, ge=0, description="Closing price")

    # Volume data
    bid_size: int = Field(default=0, ge=0, description="Bid size")
    ask_size: int = Field(default=0, ge=0, description="Ask size")
    volume: int = Field(default=0, ge=0, description="Trading volume")

    # Greeks and volatility
    implied_volatility: Optional[float] = Field(
        None, ge=0, description="Implied volatility"
    )
    historical_volatility: Optional[float] = Field(
        None, ge=0, description="Historical volatility"
    )

    # Timestamps
    timestamp: str = Field(..., description="Data timestamp")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
    )
    updated_at: Optional[str] = Field(None, alias="updatedAt")

    ALLOWED_FEED_TYPES: ClassVar[List[str]] = ["QUOTE", "TRADE", "DEPTH", "VOLATILITY"]

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol must be non-empty")
        return v.upper()

    @field_validator("feed_type")
    @classmethod
    def validate_feed_type(cls, v: str) -> str:
        if v not in cls.ALLOWED_FEED_TYPES:
            raise ValueError(f"Feed type must be one of: {cls.ALLOWED_FEED_TYPES}")
        return v

    @model_validator(mode="after")
    def validate_market_data_logic(self) -> "MarketData":
        if self.bid_price > self.ask_price:
            raise ValueError("Bid price cannot be greater than ask price")
        if self.high_price < self.low_price:
            raise ValueError("High price cannot be less than low price")
        if self.last_price < 0:
            raise ValueError("Last price cannot be negative")
        return self

    def get_spread(self) -> float:
        return self.ask_price - self.bid_price

    def get_spread_percentage(self) -> float:
        if self.bid_price == 0:
            return 0.0
        return (self.get_spread() / self.bid_price) * 100

    def get_mid_price(self) -> float:
        return (self.bid_price + self.ask_price) / 2

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
