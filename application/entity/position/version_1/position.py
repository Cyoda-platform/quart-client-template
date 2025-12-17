from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Position(CyodaEntity):
    """
    Position represents a portfolio position in the trading platform.

    Manages position lifecycle: initial_state -> created -> active -> closed
    """

    ENTITY_NAME: ClassVar[str] = "Position"
    ENTITY_VERSION: ClassVar[int] = 1

    account: str = Field(..., description="Trading account")
    instrument: str = Field(..., description="Instrument symbol")
    quantity: float = Field(..., description="Current position quantity")
    average_price: Optional[float] = Field(
        default=None, alias="averagePrice", description="Average entry price"
    )

    current_price: Optional[float] = Field(
        default=None, alias="currentPrice", description="Current market price"
    )
    market_value: Optional[float] = Field(
        default=None, alias="marketValue", description="Current market value"
    )

    realized_pnl: Optional[float] = Field(
        default=None, alias="realizedPnl", description="Realized profit/loss"
    )
    unrealized_pnl: Optional[float] = Field(
        default=None, alias="unrealizedPnl", description="Unrealized profit/loss"
    )

    opened_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="openedAt",
        description="Position opening timestamp",
    )
    closed_at: Optional[str] = Field(
        default=None, alias="closedAt", description="Position closing timestamp"
    )

    status: Optional[str] = Field(
        default=None, description="Position status (OPEN, CLOSED)"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

    def to_api_response(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        return data
