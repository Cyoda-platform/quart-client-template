"""
Instrument entity for institutional trading platform.

Represents financial instruments (equities, options, futures, swaps).
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Instrument(CyodaEntity):
    """
    Instrument represents a financial instrument (equity, option, future, swap).

    State transitions: initial_state -> active -> expired
    """

    ENTITY_NAME: ClassVar[str] = "Instrument"
    ENTITY_VERSION: ClassVar[int] = 1

    isin: str = Field(..., description="ISIN code")
    ticker: str = Field(..., description="Ticker symbol")
    instrument_type: str = Field(
        ...,
        alias="instrumentType",
        description="Type: EQUITY, OPTION, FUTURE, SWAP",
    )
    currency: str = Field(default="USD", description="Currency code")
    exchange: str = Field(..., description="Exchange code")
    last_price: Optional[float] = Field(
        default=None, alias="lastPrice", description="Last traded price"
    )
    bid_price: Optional[float] = Field(
        default=None, alias="bidPrice", description="Current bid price"
    )
    ask_price: Optional[float] = Field(
        default=None, alias="askPrice", description="Current ask price"
    )
    expiry_date: Optional[str] = Field(
        default=None, alias="expiryDate", description="Expiry date for derivatives"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Creation timestamp",
    )

    @field_validator("isin")
    @classmethod
    def validate_isin(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("ISIN must be non-empty")
        return v.strip().upper()

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Ticker must be non-empty")
        return v.strip().upper()

    @field_validator("instrument_type")
    @classmethod
    def validate_instrument_type(cls, v: str) -> str:
        valid_types = {"EQUITY", "OPTION", "FUTURE", "SWAP"}
        if v.upper() not in valid_types:
            raise ValueError(f"Invalid instrument type: {v}")
        return v.upper()
