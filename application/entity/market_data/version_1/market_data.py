from datetime import datetime, timezone
from typing import ClassVar

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class MarketData(CyodaEntity):
    """
    MarketData represents real-time market data for a trading symbol.

    Captures market quotes including bid/ask prices, last trade price,
    volume, and sequence number for order book management.
    """

    ENTITY_NAME: ClassVar[str] = "MarketData"
    ENTITY_VERSION: ClassVar[int] = 1

    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, BTC/USD)")
    exchange: str = Field(
        ..., description="Exchange identifier (e.g., NASDAQ, NYSE, BINANCE)"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Timestamp of market data snapshot (ISO 8601 format)",
    )
    bid: float = Field(..., description="Best bid price")
    ask: float = Field(..., description="Best ask price")
    last: float = Field(..., description="Last traded price")
    volume: float = Field(..., description="Trading volume in current period")
    sequence: int = Field(..., description="Sequence number for order book consistency")

    def is_valid_quote(self) -> bool:
        """Check if quote is valid (bid < ask)"""
        return self.bid < self.ask

    def get_mid_price(self) -> float:
        """Calculate mid price between bid and ask"""
        return (self.bid + self.ask) / 2

    def get_spread(self) -> float:
        """Calculate bid-ask spread"""
        return self.ask - self.bid
