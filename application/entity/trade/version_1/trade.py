"""
Trade entity for institutional trading platform.

Represents executed trades with settlement tracking.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Trade(CyodaEntity):
    """
    Trade represents an executed trade.
    
    State: initial_state -> created -> settled -> completed
    """

    ENTITY_NAME: ClassVar[str] = "Trade"
    ENTITY_VERSION: ClassVar[int] = 1

    order_id: str = Field(..., alias="orderId", description="Related order ID")
    account_id: str = Field(..., alias="accountId", description="Account ID")
    instrument_id: str = Field(..., alias="instrumentId", description="Instrument ID")
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., description="Trade quantity")
    price: float = Field(..., description="Execution price")
    commission: float = Field(default=0.0, description="Commission paid")
    settlement_date: Optional[str] = Field(
        default=None, alias="settlementDate", description="Settlement date"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Trade execution timestamp",
    )

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v.upper() not in {"BUY", "SELL"}:
            raise ValueError("Side must be BUY or SELL")
        return v.upper()

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v

