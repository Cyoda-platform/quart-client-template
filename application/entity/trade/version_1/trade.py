from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Trade(CyodaEntity):
    """
    Trade represents an executed trade in the trading platform.

    Manages trade lifecycle: initial_state -> created -> confirmed -> settled
    """

    ENTITY_NAME: ClassVar[str] = "Trade"
    ENTITY_VERSION: ClassVar[int] = 1

    trade_id: Optional[str] = Field(
        default=None, alias="tradeId", description="Unique trade identifier"
    )
    order_id: str = Field(..., alias="orderId", description="Related order ID")
    instrument: str = Field(..., description="Instrument symbol")
    side: str = Field(..., description="BUY or SELL")
    quantity: float = Field(..., gt=0, description="Trade quantity")
    price: float = Field(..., gt=0, description="Execution price")
    counterparty: str = Field(..., description="Counterparty identifier")

    executed_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="executedAt",
        description="Trade execution timestamp",
    )
    confirmed_at: Optional[str] = Field(
        default=None, alias="confirmedAt", description="Trade confirmation timestamp"
    )

    gross_amount: Optional[float] = Field(
        default=None, alias="grossAmount", description="Gross trade amount"
    )
    commission: Optional[float] = Field(default=None, description="Commission charged")
    net_amount: Optional[float] = Field(
        default=None, alias="netAmount", description="Net trade amount"
    )

    status: Optional[str] = Field(
        default=None, description="Trade status (PENDING, CONFIRMED, SETTLED)"
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
