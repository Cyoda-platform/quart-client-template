from common.entity.cyoda_entity import CyodaEntity
from pydantic import Field, field_validator
from datetime import datetime, timezone
from typing import ClassVar, Optional, List, Literal, Dict

class MarketData(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "MarketData"
    ENTITY_VERSION: ClassVar[int] = 1

    symbol: str = Field(..., description="Stock/Asset symbol")
    price: float = Field(..., description="Current market price")
    price_type: Literal["BID", "ASK", "LAST"] = Field(default="LAST", description="Price type")
    volume: int = Field(..., description="Trading volume")
    timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Timestamp of market data"
    )
    market: str = Field(..., description="Market/Exchange name")
    instrument_type: Literal["STOCK", "OPTION", "FUTURE", "CRYPTO"] = Field(..., description="Type of financial instrument")

    historical_prices: Optional[List[Dict[str, float]]] = Field(
        default=None,
        description="Recent historical price data"
    )

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be a positive number")
        return v

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Volume cannot be negative")
        return v