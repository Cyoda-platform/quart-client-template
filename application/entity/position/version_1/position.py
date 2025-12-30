"""
Position entity for institutional trading platform.

Represents real-time positions per account and strategy.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Position represents a real-time position in an instrument.

    State: initial_state -> active -> closed
    """

    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    instrument_id: str = Field(..., alias="instrumentId", description="Instrument ID")
    quantity: float = Field(..., description="Current position quantity")
    average_cost: float = Field(
        ..., alias="averageCost", description="Average cost per unit"
    )
    current_price: Optional[float] = Field(
        default=None, alias="currentPrice", description="Current market price"
    )
    unrealized_pnl: Optional[float] = Field(
        default=None, alias="unrealizedPnl", description="Unrealized P&L"
    )
    realized_pnl: float = Field(
        default=0.0, alias="realizedPnl", description="Realized P&L"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Creation timestamp",
    )

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Quantity cannot be negative")
        return v

    @field_validator("average_cost")
    @classmethod
    def validate_average_cost(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Average cost cannot be negative")
        return v
