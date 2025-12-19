from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class MarketData(CyodaEntity):
    """
    MarketData represents real-time market data (ticks, quotes, orderbook).
    State transitions: initial_state -> received -> normalized -> published
    """

    ENTITY_NAME: ClassVar[str] = "MarketData"
    ENTITY_VERSION: ClassVar[int] = 1

    symbol: str = Field(..., description="Trading symbol")
    data_type: str = Field(..., description="Data type: TICK, QUOTE, ORDERBOOK")
    bid_price: Optional[float] = Field(None, ge=0, description="Best bid price")
    ask_price: Optional[float] = Field(None, ge=0, description="Best ask price")
    bid_size: Optional[float] = Field(None, ge=0, description="Bid size")
    ask_size: Optional[float] = Field(None, ge=0, description="Ask size")
    last_price: Optional[float] = Field(None, ge=0, description="Last trade price")
    last_size: Optional[float] = Field(None, ge=0, description="Last trade size")
    venue_id: str = Field(..., description="Source venue ID")
    sequence_number: int = Field(..., ge=0, description="Sequence number for ordering")
    received_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Data reception timestamp",
    )
    published_at: Optional[str] = Field(None, description="Publication timestamp")

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v: str) -> str:
        if v not in ["TICK", "QUOTE", "ORDERBOOK"]:
            raise ValueError("data_type must be TICK, QUOTE, or ORDERBOOK")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
