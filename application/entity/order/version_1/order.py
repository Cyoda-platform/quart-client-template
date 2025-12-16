from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class Order(CyodaEntity):
    """
    Order represents a trading order in the real-time trading platform.
    
    Manages order lifecycle from creation through execution or cancellation.
    """

    ENTITY_NAME: ClassVar[str] = "Order"
    ENTITY_VERSION: ClassVar[int] = 1

    order_id: str = Field(..., description="Business identifier for the order")
    account_id: str = Field(..., description="Account that placed the order")
    instrument_id: str = Field(..., description="Instrument being traded")
    side: str = Field(..., description="Order side: BUY or SELL")
    type: str = Field(..., description="Order type: MARKET, LIMIT, STOP")
    quantity: float = Field(..., description="Order quantity")
    price: Optional[float] = Field(None, description="Order price (for LIMIT orders)")
    status: str = Field(default="New", description="Order status")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Order creation timestamp"
    )
    filled_quantity: float = Field(default=0.0, description="Quantity filled so far")
    average_price: Optional[float] = Field(None, description="Average execution price")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

