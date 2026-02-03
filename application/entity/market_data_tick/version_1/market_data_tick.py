"""
MarketDataTick entity for real-time market data ingestion.

Represents market data: initial_state -> ingested -> normalized -> published
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class MarketDataTick(CyodaEntity):
    """
    MarketDataTick represents a market data update from a venue.
    Manages market data lifecycle from ingestion through normalization and publication.
    """

    ENTITY_NAME: ClassVar[str] = "MarketDataTick"
    ENTITY_VERSION: ClassVar[int] = 1

    instrument_id: str = Field(..., alias="instrumentId", description="Security identifier")
    bid: float = Field(..., ge=0, description="Best bid price")
    ask: float = Field(..., ge=0, description="Best ask price")
    last: Optional[float] = Field(default=None, ge=0, description="Last trade price")
    bid_size: float = Field(default=0.0, alias="bidSize", ge=0, description="Bid size")
    ask_size: float = Field(default=0.0, alias="askSize", ge=0, description="Ask size")
    venue: str = Field(..., description="Data source venue")
    timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Quote timestamp",
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt",
        description="Ingestion timestamp",
    )

    @field_validator("ask", "bid")
    @classmethod
    def validate_bid_ask(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Bid/Ask cannot be negative")
        return v

    model_config = ConfigDict(populate_by_name=True, validate_assignment=True, extra="allow")

