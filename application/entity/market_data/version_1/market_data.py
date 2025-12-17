"""
MarketData entity for trading platform.

Represents real-time and historical market data including bid/ask prices,
last traded prices, and volume information from various market data sources.
"""

from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class MarketData(CyodaEntity):
    """
    MarketData entity representing market data for financial instruments.

    Captures bid/ask quotes, last traded prices, and volume data
    from various market data sources and exchanges.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "MarketData"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core market data fields
    instrument_id: str = Field(
        ..., alias="instrumentId", description="Identifier of the instrument"
    )
    timestamp: str = Field(..., description="Timestamp of market data (ISO 8601)")
    source: str = Field(
        ..., description="Source of market data (e.g., EXCHANGE_A, NASDAQ)"
    )

    # Optional price fields
    bid: Optional[float] = Field(default=None, description="Current bid price")
    ask: Optional[float] = Field(default=None, description="Current ask price")
    last_price: Optional[float] = Field(
        default=None, alias="lastPrice", description="Last traded price"
    )
    volume: Optional[float] = Field(default=None, description="Trading volume")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
