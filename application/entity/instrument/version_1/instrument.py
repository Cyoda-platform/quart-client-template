from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Instrument(CyodaEntity):
    """
    Instrument represents a tradable security or derivative.

    Defines the characteristics of instruments available for trading.
    """

    ENTITY_NAME: ClassVar[str] = "Instrument"
    ENTITY_VERSION: ClassVar[int] = 1

    instrument_id: str = Field(
        ..., description="Business identifier for the instrument"
    )
    symbol: str = Field(..., description="Trading symbol")
    type: str = Field(..., description="Instrument type: STOCK, FUTURE, OPTION, etc.")
    expiry_date: Optional[str] = Field(
        None, description="Expiry date for derivatives (ISO 8601)"
    )
    currency: str = Field(..., description="Trading currency")
    lot_size: float = Field(..., description="Minimum trading lot size")
    status: str = Field(default="Active", description="Instrument status")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
