# entity/instrument/version_1/instrument.py

"""
Instrument Entity for Trading Platform

Represents tradeable securities including equities, derivatives, bonds, and other financial instruments.
Manages instrument metadata, trading specifications, and lifecycle states.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional
from decimal import Decimal

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Instrument(CyodaEntity):
    """
    Instrument represents a tradeable financial security with complete metadata
    and trading specifications for the trading platform.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Instrument"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core identification fields
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, MSFT)")
    name: str = Field(..., description="Full instrument name")
    isin: Optional[str] = Field(default=None, description="International Securities Identification Number")
    cusip: Optional[str] = Field(default=None, description="Committee on Uniform Securities Identification Procedures number")

    # Classification fields
    instrument_type: str = Field(..., alias="instrumentType", description="Type of instrument (EQUITY, OPTION, FUTURE, BOND)")
    asset_class: str = Field(..., alias="assetClass", description="Asset class (EQUITY, FIXED_INCOME, DERIVATIVE, COMMODITY)")
    exchange: str = Field(..., description="Primary exchange (NYSE, NASDAQ, CME)")
    currency: str = Field(..., description="Trading currency (USD, EUR, GBP)")

    # Trading specifications
    tick_size: Optional[Decimal] = Field(default=None, alias="tickSize", description="Minimum price increment")
    lot_size: Optional[int] = Field(default=None, alias="lotSize", description="Standard trading lot size")
    multiplier: Optional[Decimal] = Field(default=None, description="Contract multiplier for derivatives")

    # Market data fields
    last_price: Optional[Decimal] = Field(default=None, alias="lastPrice", description="Last traded price")
    bid_price: Optional[Decimal] = Field(default=None, alias="bidPrice", description="Current bid price")
    ask_price: Optional[Decimal] = Field(default=None, alias="askPrice", description="Current ask price")

    # Status and lifecycle
    is_active: bool = Field(default=True, alias="isActive", description="Whether instrument is actively tradeable")
    listing_date: Optional[str] = Field(default=None, alias="listingDate", description="Date when instrument was listed")
    delisting_date: Optional[str] = Field(default=None, alias="delistingDate", description="Date when instrument was delisted")

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when instrument was created"
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt", 
        description="Timestamp when instrument was last updated"
    )

    # Validation constants
    VALID_INSTRUMENT_TYPES: ClassVar[List[str]] = ["EQUITY", "OPTION", "FUTURE", "BOND", "ETF", "INDEX"]
    VALID_ASSET_CLASSES: ClassVar[List[str]] = ["EQUITY", "FIXED_INCOME", "DERIVATIVE", "COMMODITY", "CURRENCY"]
    VALID_CURRENCIES: ClassVar[List[str]] = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD"]

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate trading symbol format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol must be non-empty")
        if len(v) > 20:
            raise ValueError("Symbol must be at most 20 characters")
        return v.strip().upper()

    @field_validator("instrument_type")
    @classmethod
    def validate_instrument_type(cls, v: str) -> str:
        """Validate instrument type"""
        if v not in cls.VALID_INSTRUMENT_TYPES:
            raise ValueError(f"Instrument type must be one of: {cls.VALID_INSTRUMENT_TYPES}")
        return v

    @field_validator("asset_class")
    @classmethod
    def validate_asset_class(cls, v: str) -> str:
        """Validate asset class"""
        if v not in cls.VALID_ASSET_CLASSES:
            raise ValueError(f"Asset class must be one of: {cls.VALID_ASSET_CLASSES}")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code"""
        if v not in cls.VALID_CURRENCIES:
            raise ValueError(f"Currency must be one of: {cls.VALID_CURRENCIES}")
        return v

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def update_market_data(self, last_price: Optional[Decimal] = None, 
                          bid_price: Optional[Decimal] = None, 
                          ask_price: Optional[Decimal] = None) -> None:
        """Update market data prices"""
        if last_price is not None:
            self.last_price = last_price
        if bid_price is not None:
            self.bid_price = bid_price
        if ask_price is not None:
            self.ask_price = ask_price
        self.update_timestamp()

    def is_tradeable(self) -> bool:
        """Check if instrument is currently tradeable"""
        return self.is_active and self.delisting_date is None

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
