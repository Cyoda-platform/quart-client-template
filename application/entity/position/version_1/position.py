"""
Position entity for portfolio tracking in institutional trading platform.

Represents a position: initial_state -> open -> monitored -> closed
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Position represents a portfolio position with real-time P&L tracking.
    Manages position lifecycle from opening through monitoring to closure.
    """

    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., description="Account ID holding the position")
    instrument_id: str = Field(..., description="Security identifier")
    quantity: float = Field(..., description="Position quantity (positive=long, negative=short)")
    avg_cost: float = Field(..., alias="avgCost", description="Average cost per unit")
    current_price: float = Field(..., alias="currentPrice", description="Current market price")
    realized_pnl: float = Field(default=0.0, alias="realizedPnl", description="Realized P&L")
    unrealized_pnl: float = Field(default=0.0, alias="unrealizedPnl", description="Unrealized P&L")
    currency: str = Field(default="USD", description="Position currency")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt",
        description="Position creation timestamp",
    )
    updated_at: Optional[str] = Field(default=None, alias="updatedAt", description="Last update timestamp")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v == 0:
            raise ValueError("Quantity cannot be zero")
        return v

    @field_validator("avg_cost", "current_price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v

    model_config = ConfigDict(populate_by_name=True, validate_assignment=True, extra="allow")

