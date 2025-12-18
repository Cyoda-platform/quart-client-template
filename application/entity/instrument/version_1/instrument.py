"""
Instrument entity for trading platform.

Represents financial instruments (equities, options, futures) with metadata
for market data ingestion and order routing.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Instrument(CyodaEntity):
    """
    Represents a financial instrument (equity, option, future).
    
    Manages instrument metadata including symbol, type, and exchange information.
    State transitions: initial_state -> active -> inactive
    """

    ENTITY_NAME: ClassVar[str] = "Instrument"
    ENTITY_VERSION: ClassVar[int] = 1

    symbol: str = Field(..., description="Unique instrument symbol (e.g., AAPL)")
    instrument_type: str = Field(
        ..., alias="instrumentType", description="Type: EQUITY, OPTION, FUTURE"
    )
    exchange: str = Field(..., description="Exchange code (e.g., NYSE, NASDAQ)")
    currency: str = Field(default="USD", description="Trading currency")
    tick_size: float = Field(
        default=0.01, alias="tickSize", description="Minimum price increment"
    )
    lot_size: int = Field(
        default=1, alias="lotSize", description="Standard lot size"
    )
    is_active: bool = Field(
        default=True, alias="isActive", description="Whether instrument is tradeable"
    )
    underlying_symbol: Optional[str] = Field(
        default=None,
        alias="underlyingSymbol",
        description="For derivatives: underlying asset symbol",
    )
    expiry_date: Optional[str] = Field(
        default=None, alias="expiryDate", description="For derivatives: expiry date"
    )
    strike_price: Optional[float] = Field(
        default=None, alias="strikePrice", description="For options: strike price"
    )
    option_type: Optional[str] = Field(
        default=None, alias="optionType", description="For options: CALL or PUT"
    )

    def is_equity(self) -> bool:
        return self.instrument_type == "EQUITY"

    def is_derivative(self) -> bool:
        return self.instrument_type in ("OPTION", "FUTURE")

    def is_tradeable(self) -> bool:
        return self.is_active and self.state == "active"

