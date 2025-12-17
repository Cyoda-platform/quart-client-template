from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class MarketData(CyodaEntity):
    """
    MarketData represents market data in the trading platform.

    Manages market data lifecycle: initial_state -> created -> normalized -> published
    """

    ENTITY_NAME: ClassVar[str] = "MarketData"
    ENTITY_VERSION: ClassVar[int] = 1

    instrument: str = Field(..., description="Instrument symbol")
    feed_source: str = Field(..., alias="feedSource", description="Data feed source")
    data_type: str = Field(..., alias="dataType", description="Level1 or Level2")

    bid_price: Optional[float] = Field(
        default=None, alias="bidPrice", description="Best bid price"
    )
    bid_size: Optional[float] = Field(
        default=None, alias="bidSize", description="Bid size"
    )
    ask_price: Optional[float] = Field(
        default=None, alias="askPrice", description="Best ask price"
    )
    ask_size: Optional[float] = Field(
        default=None, alias="askSize", description="Ask size"
    )
    last_price: Optional[float] = Field(
        default=None, alias="lastPrice", description="Last trade price"
    )
    last_size: Optional[float] = Field(
        default=None, alias="lastSize", description="Last trade size"
    )

    volume: Optional[float] = Field(default=None, description="Trading volume")
    high: Optional[float] = Field(default=None, description="Daily high")
    low: Optional[float] = Field(default=None, description="Daily low")

    received_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="receivedAt",
        description="Data reception timestamp",
    )
    normalized_at: Optional[str] = Field(
        default=None, alias="normalizedAt", description="Normalization timestamp"
    )

    status: Optional[str] = Field(
        default=None, description="Data status (RECEIVED, NORMALIZED, PUBLISHED)"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

    def to_api_response(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        return data

