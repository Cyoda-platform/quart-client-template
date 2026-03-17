"""
Instrument entity for institutional trading platform.

Defines market instruments (equities, derivatives) with metadata and trading parameters.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Instrument(CyodaEntity):
    """
    Instrument represents a tradable market instrument in the system.
    
    Supports equities and OTC derivatives with metadata and trading parameters.
    States: active -> inactive
    """

    ENTITY_NAME: ClassVar[str] = "Instrument"
    ENTITY_VERSION: ClassVar[int] = 1

    # Instrument identification
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, EURUSD)")
    isin: Optional[str] = Field(default=None, description="ISIN code")
    cusip: Optional[str] = Field(default=None, description="CUSIP code")
    
    # Instrument details
    name: str = Field(..., description="Instrument name")
    instrument_type: str = Field(
        ..., alias="instrumentType", description="Type: equity, derivative, option, future"
    )
    currency: str = Field(..., description="Trading currency (EUR, USD, GBP, etc.)")
    
    # Venue information
    primary_venue: str = Field(
        ..., alias="primaryVenue", description="Primary trading venue (LSE, Euronext, XETRA)"
    )
    supported_venues: Optional[str] = Field(
        default=None, alias="supportedVenues", description="Comma-separated list of supported venues"
    )
    
    # Trading parameters
    tick_size: Optional[float] = Field(
        default=None, alias="tickSize", description="Minimum price increment"
    )
    lot_size: Optional[float] = Field(
        default=None, alias="lotSize", description="Standard lot size"
    )
    min_order_size: Optional[float] = Field(
        default=None, alias="minOrderSize", description="Minimum order size"
    )
    max_order_size: Optional[float] = Field(
        default=None, alias="maxOrderSize", description="Maximum order size"
    )
    
    # Derivative-specific fields
    underlying_symbol: Optional[str] = Field(
        default=None, alias="underlyingSymbol", description="Underlying instrument symbol"
    )
    expiry_date: Optional[str] = Field(
        default=None, alias="expiryDate", description="Expiry date (for derivatives)"
    )
    strike_price: Optional[float] = Field(
        default=None, alias="strikePrice", description="Strike price (for options)"
    )
    
    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt",
        description="Instrument creation timestamp",
    )
    last_updated_at: Optional[str] = Field(
        default=None, alias="lastUpdatedAt", description="Last update timestamp"
    )

    @field_validator("instrument_type")
    @classmethod
    def validate_instrument_type(cls, v: str) -> str:
        """Validate instrument type"""
        valid_types = ["equity", "derivative", "option", "future"]
        if v not in valid_types:
            raise ValueError(f"Instrument type must be one of: {valid_types}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code"""
        if len(v) != 3:
            raise ValueError("Currency must be a 3-letter code")
        return v.upper()

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

