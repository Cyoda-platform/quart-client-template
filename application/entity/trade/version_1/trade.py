from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class Trade(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "Trade"
    ENTITY_VERSION: ClassVar[int] = 1

    trade_id: str = Field(..., description="Unique business ID for the trade")
    order_id: str = Field(..., description="Order ID")
    instrument_id: str = Field(..., description="Instrument ID (technical ID)")
    quantity: float = Field(..., description="Trade quantity")
    price: float = Field(..., description="Trade price")
    execution_time: Optional[str] = Field(default=None, description="ISO timestamp")

    # Internal workflow fields
    processing_status: Optional[str] = Field(
        default="PENDING", description="Internal processing status"
    )
