from datetime import datetime, timezone
from typing import ClassVar

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Trade(CyodaEntity):
    """
    Trade represents an executed trade between buy and sell orders.
    
    Records the matching and execution details of orders.
    """

    ENTITY_NAME: ClassVar[str] = "Trade"
    ENTITY_VERSION: ClassVar[int] = 1

    trade_id: str = Field(..., description="Business identifier for the trade")
    buy_order_id: str = Field(..., description="Buy order ID")
    sell_order_id: str = Field(..., description="Sell order ID")
    instrument_id: str = Field(..., description="Instrument traded")
    quantity: float = Field(..., description="Trade quantity")
    price: float = Field(..., description="Trade execution price")
    trade_time: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Trade execution timestamp"
    )
    status: str = Field(default="Open", description="Trade status")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

