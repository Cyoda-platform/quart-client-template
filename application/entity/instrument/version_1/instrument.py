from typing import ClassVar

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Instrument(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Instrument"
    ENTITY_VERSION: ClassVar[int] = 1

    symbol: str = Field(..., description="Trading symbol (e.g., AAPL)")
    exchange: str = Field(..., description="Exchange name (e.g., NASDAQ)")
    instrument_type: str = Field(..., description="Type (EQUITY, OPTION, FUTURE)")
    currency: str = Field(default="USD", description="Trading currency")
