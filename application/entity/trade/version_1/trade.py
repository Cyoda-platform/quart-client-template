from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Trade(CyodaEntity):
    """
    Trade represents an executed trade resulting from order fills.
    State transitions: initial_state -> executed -> settled/failed
    """

    ENTITY_NAME: ClassVar[str] = "Trade"
    ENTITY_VERSION: ClassVar[int] = 1

    order_id: str = Field(..., description="Source order ID")
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="Trade side: BUY or SELL")
    quantity: float = Field(..., gt=0, description="Trade quantity")
    price: float = Field(..., gt=0, description="Execution price")
    account_id: str = Field(..., description="Account ID")
    venue_id: str = Field(..., description="Venue ID")
    trade_id: str = Field(..., description="Unique trade identifier from venue")
    commission: float = Field(default=0, ge=0, description="Commission paid")
    executed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Trade execution timestamp"
    )
    settled_at: Optional[str] = Field(None, description="Settlement timestamp")

    @field_validator("side")
    @classmethod
    def validate_side(cls, v: str) -> str:
        if v not in ["BUY", "SELL"]:
            raise ValueError("side must be BUY or SELL")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

