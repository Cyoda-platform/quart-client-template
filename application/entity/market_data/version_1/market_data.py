"""
MarketData Entity for Real-Time Trading Platform

Represents real-time market data feeds with price, volume, and market status tracking
for equities and derivatives as specified in functional requirements.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class MarketData(CyodaEntity):
    """
    MarketData entity represents real-time market data feeds with price, volume,
    and market status tracking for trading instruments.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> validated -> enriched -> published
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "MarketData"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, SPY)")
    instrument_type: str = Field(
        ..., 
        alias="instrumentType",
        description="Instrument type: EQUITY or DERIVATIVE"
    )
    price: float = Field(..., description="Current market price")
    volume: int = Field(..., description="Trading volume")
    market_status: str = Field(
        ..., 
        alias="marketStatus",
        description="Market status: OPEN, CLOSED, PRE_MARKET, AFTER_HOURS"
    )
    timestamp: str = Field(..., description="Data timestamp (ISO 8601 format)")
    exchange: str = Field(..., description="Exchange identifier")

    # Optional price fields
    bid_price: Optional[float] = Field(
        default=None, 
        alias="bidPrice",
        description="Best bid price"
    )
    ask_price: Optional[float] = Field(
        default=None, 
        alias="askPrice",
        description="Best ask price"
    )

    # Processing-related fields (populated during enrichment)
    spread: Optional[float] = Field(
        default=None,
        description="Bid-ask spread calculated during enrichment"
    )
    volatility: Optional[float] = Field(
        default=None,
        description="Price volatility calculated during enrichment"
    )
    enrichment_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="enrichmentData",
        description="Additional data populated during enrichment"
    )

    # Validation constants
    ALLOWED_INSTRUMENT_TYPES: ClassVar[List[str]] = ["EQUITY", "DERIVATIVE"]
    ALLOWED_MARKET_STATUSES: ClassVar[List[str]] = [
        "OPEN", "CLOSED", "PRE_MARKET", "AFTER_HOURS"
    ]

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, v: str) -> str:
        """Validate trading symbol format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Symbol must be non-empty")
        if len(v) > 20:
            raise ValueError("Symbol must be at most 20 characters long")
        return v.strip().upper()

    @field_validator("instrument_type")
    @classmethod
    def validate_instrument_type(cls, v: str) -> str:
        """Validate instrument type"""
        if v not in cls.ALLOWED_INSTRUMENT_TYPES:
            raise ValueError(f"Instrument type must be one of: {cls.ALLOWED_INSTRUMENT_TYPES}")
        return v

    @field_validator("price", "bid_price", "ask_price")
    @classmethod
    def validate_prices(cls, v: Optional[float]) -> Optional[float]:
        """Validate price fields are positive"""
        if v is not None and v <= 0:
            raise ValueError("Prices must be positive")
        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v: int) -> int:
        """Validate volume is non-negative"""
        if v < 0:
            raise ValueError("Volume must be non-negative")
        return v

    @field_validator("market_status")
    @classmethod
    def validate_market_status(cls, v: str) -> str:
        """Validate market status"""
        if v not in cls.ALLOWED_MARKET_STATUSES:
            raise ValueError(f"Market status must be one of: {cls.ALLOWED_MARKET_STATUSES}")
        return v

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, v: str) -> str:
        """Validate exchange identifier"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Exchange must be non-empty")
        if len(v) > 10:
            raise ValueError("Exchange must be at most 10 characters long")
        return v.strip().upper()

    def calculate_spread(self) -> Optional[float]:
        """Calculate bid-ask spread if both prices are available"""
        if self.bid_price is not None and self.ask_price is not None:
            return self.ask_price - self.bid_price
        return None

    def set_enrichment_data(self, enrichment_data: Dict[str, Any]) -> None:
        """Set enrichment data and calculate derived fields"""
        self.enrichment_data = enrichment_data
        self.spread = self.calculate_spread()
        self.update_timestamp()

    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        return self.market_status == "OPEN"

    def is_stale(self, max_age_seconds: int = 60) -> bool:
        """Check if market data is stale based on timestamp"""
        try:
            data_time = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))
            current_time = datetime.now(timezone.utc)
            age_seconds = (current_time - data_time).total_seconds()
            return age_seconds > max_age_seconds
        except (ValueError, AttributeError):
            return True  # Consider invalid timestamps as stale

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        # Add state for API compatibility
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
