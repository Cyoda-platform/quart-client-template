from datetime import datetime, timezone
from typing import ClassVar

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class MarketQuote(CyodaEntity):
    """
    MarketQuote represents real-time market pricing data.

    Contains bid/ask prices and sizes for an instrument.
    """

    ENTITY_NAME: ClassVar[str] = "MarketQuote"
    ENTITY_VERSION: ClassVar[int] = 1

    instrument_id: str = Field(..., description="Instrument identifier")
    bid_price: float = Field(..., description="Current bid price")
    ask_price: float = Field(..., description="Current ask price")
    bid_size: float = Field(..., description="Bid size at bid price")
    ask_size: float = Field(..., description="Ask size at ask price")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Quote timestamp",
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
