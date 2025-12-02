"""
Instrument Entity for Real-Time Trading Platform

Represents financial instruments (equities and derivatives) with trading parameters,
contract specifications, and exchange information.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Instrument(CyodaEntity):
    """
    Instrument entity represents financial instruments (equities and derivatives)
    with trading parameters and contract specifications.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> validated -> active
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Instrument"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    symbol: str = Field(..., description="Trading symbol (e.g., AAPL, SPY)")
    instrument_type: str = Field(
        ..., 
        alias="instrumentType",
        description="Instrument type: EQUITY or DERIVATIVE"
    )
    name: str = Field(..., description="Full instrument name")
    exchange: str = Field(..., description="Primary exchange")
    currency: str = Field(..., description="Trading currency (e.g., USD, EUR)")
    lot_size: int = Field(
        ..., 
        alias="lotSize",
        description="Minimum trading unit"
    )
    tick_size: float = Field(
        ..., 
        alias="tickSize",
        description="Minimum price increment"
    )
    is_tradable: bool = Field(
        ..., 
        alias="isTradable",
        description="Trading status flag"
    )

    # Optional derivative contract specifications
    contract_specs: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="contractSpecs",
        description="Derivative contract specifications (for derivatives only)"
    )

    # Additional trading parameters
    margin_requirement: Optional[float] = Field(
        default=None,
        alias="marginRequirement",
        description="Margin requirement percentage"
    )
    max_order_size: Optional[int] = Field(
        default=None,
        alias="maxOrderSize",
        description="Maximum order size allowed"
    )
    trading_hours: Optional[Dict[str, str]] = Field(
        default=None,
        alias="tradingHours",
        description="Trading hours information"
    )

    # Setup-related fields (populated during setup)
    setup_data: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="setupData",
        description="Data populated during instrument setup"
    )

    # Validation constants
    ALLOWED_INSTRUMENT_TYPES: ClassVar[List[str]] = ["EQUITY", "DERIVATIVE"]
    ALLOWED_CURRENCIES: ClassVar[List[str]] = [
        "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY"
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

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate instrument name"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Name must be non-empty")
        if len(v) > 200:
            raise ValueError("Name must be at most 200 characters long")
        return v.strip()

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, v: str) -> str:
        """Validate exchange identifier"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Exchange must be non-empty")
        if len(v) > 10:
            raise ValueError("Exchange must be at most 10 characters long")
        return v.strip().upper()

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code"""
        currency_upper = v.upper()
        if currency_upper not in cls.ALLOWED_CURRENCIES:
            raise ValueError(f"Currency must be one of: {cls.ALLOWED_CURRENCIES}")
        return currency_upper

    @field_validator("lot_size")
    @classmethod
    def validate_lot_size(cls, v: int) -> int:
        """Validate lot size is positive"""
        if v <= 0:
            raise ValueError("Lot size must be positive")
        return v

    @field_validator("tick_size")
    @classmethod
    def validate_tick_size(cls, v: float) -> float:
        """Validate tick size is positive"""
        if v <= 0:
            raise ValueError("Tick size must be positive")
        return v

    @field_validator("margin_requirement")
    @classmethod
    def validate_margin_requirement(cls, v: Optional[float]) -> Optional[float]:
        """Validate margin requirement is between 0 and 100"""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Margin requirement must be between 0 and 100 percent")
        return v

    @field_validator("max_order_size")
    @classmethod
    def validate_max_order_size(cls, v: Optional[int]) -> Optional[int]:
        """Validate max order size is positive"""
        if v is not None and v <= 0:
            raise ValueError("Max order size must be positive")
        return v

    def is_derivative(self) -> bool:
        """Check if instrument is a derivative"""
        return self.instrument_type == "DERIVATIVE"

    def is_equity(self) -> bool:
        """Check if instrument is an equity"""
        return self.instrument_type == "EQUITY"

    def requires_margin(self) -> bool:
        """Check if instrument requires margin"""
        return self.margin_requirement is not None and self.margin_requirement > 0

    def set_setup_data(self, setup_data: Dict[str, Any]) -> None:
        """Set setup data and update timestamp"""
        self.setup_data = setup_data
        self.update_timestamp()

    def validate_order_size(self, order_size: int) -> bool:
        """Validate if order size is within limits"""
        # Check lot size alignment
        if order_size % self.lot_size != 0:
            return False
        
        # Check maximum order size if specified
        if self.max_order_size is not None and order_size > self.max_order_size:
            return False
            
        return True

    def calculate_minimum_price_increment(self, price: float) -> float:
        """Calculate the next valid price increment"""
        return price + self.tick_size

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
