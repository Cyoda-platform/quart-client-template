"""
Instrument entity for trading platform.

Represents a tradable financial instrument (equity, future, option, etc.)
with reference data for the trading system.
"""

from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Instrument(CyodaEntity):
    """
    Instrument entity representing a tradable financial instrument.

    Supports equities, futures, and options with necessary reference data
    for order management, risk controls, and position tracking.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Instrument"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core instrument fields
    symbol: str = Field(..., description="Trading symbol/ticker")
    instrument_type: str = Field(
        ..., alias="instrumentType", description="Instrument type: EQUITY, FUTURE, OPTION"
    )
    exchange: str = Field(..., description="Primary exchange where instrument trades")
    currency: str = Field(..., description="Currency of the instrument")

    # Optional fields
    description: Optional[str] = Field(
        default=None, description="Human-readable description of instrument"
    )
    lot_size: Optional[float] = Field(
        default=None, alias="lotSize", description="Minimum tradable quantity"
    )
    tick_size: Optional[float] = Field(
        default=None, alias="tickSize", description="Minimum price increment"
    )
    multiplier: Optional[float] = Field(
        default=None, description="Contract multiplier for derivatives"
    )

    # Derivative-specific fields
    underlying_symbol: Optional[str] = Field(
        default=None, alias="underlyingSymbol", description="Underlying symbol for derivatives"
    )
    expiry_date: Optional[str] = Field(
        default=None, alias="expiryDate", description="Expiry date for derivatives (ISO 8601)"
    )
    strike_price: Optional[float] = Field(
        default=None, alias="strikePrice", description="Strike price for options"
    )
    option_type: Optional[str] = Field(
        default=None, alias="optionType", description="Option type: CALL or PUT"
    )

    # Trading status
    is_tradable: bool = Field(
        default=True, alias="isTradable", description="Whether instrument is currently tradable"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
