"""
MarketQuote entity for trading platform.

Represents real-time market quotes (bid/ask) with tick history
for market data ingestion and normalization.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class MarketQuote(CyodaEntity):
    """
    Represents a market quote in the trading system.
    
    Manages quote lifecycle: initial_state -> published -> archived
    """

    ENTITY_NAME: ClassVar[str] = "MarketQuote"
    ENTITY_VERSION: ClassVar[int] = 1

    symbol: str = Field(..., description="Instrument symbol")
    exchange: str = Field(..., description="Exchange code")
    bid_price: float = Field(..., alias="bidPrice", description="Best bid price")
    bid_size: float = Field(..., alias="bidSize", description="Bid quantity")
    ask_price: float = Field(..., alias="askPrice", description="Best ask price")
    ask_size: float = Field(..., alias="askSize", description="Ask quantity")
    last_price: Optional[float] = Field(
        default=None, alias="lastPrice", description="Last trade price"
    )
    last_size: Optional[float] = Field(
        default=None, alias="lastSize", description="Last trade size"
    )
    volume: float = Field(default=0.0, description="Daily volume")
    open_price: Optional[float] = Field(
        default=None, alias="openPrice", description="Opening price"
    )
    high_price: Optional[float] = Field(
        default=None, alias="highPrice", description="Daily high"
    )
    low_price: Optional[float] = Field(
        default=None, alias="lowPrice", description="Daily low"
    )
    close_price: Optional[float] = Field(
        default=None, alias="closePrice", description="Previous close"
    )
    quote_time: str = Field(..., alias="quoteTime", description="Quote timestamp")
    sequence_number: int = Field(
        ..., alias="sequenceNumber", description="Quote sequence for ordering"
    )

    def spread(self) -> float:
        return self.ask_price - self.bid_price

    def mid_price(self) -> float:
        return (self.bid_price + self.ask_price) / 2.0

