from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Position represents a current holding in an account.
    State transitions: initial_state -> open -> closed
    """

    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., description="Account ID")
    symbol: str = Field(..., description="Trading symbol")
    quantity: float = Field(..., description="Current quantity (positive=long, negative=short)")
    average_cost: float = Field(..., ge=0, description="Average cost per unit")
    current_price: float = Field(..., ge=0, description="Current market price")
    realized_pnl: float = Field(default=0, description="Realized profit/loss")
    unrealized_pnl: float = Field(default=0, description="Unrealized profit/loss")
    margin_required: float = Field(default=0, ge=0, description="Margin requirement")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Position creation timestamp"
    )
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

