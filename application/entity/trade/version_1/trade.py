from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity
from application.entity.order.version_1.order import OrderSide

class Trade(CyodaEntity):
    """
    Represents an executed order or a partial fill of an order.
    """
    ENTITY_NAME = "trade"
    ENTITY_VERSION = 1

    order_id: str = Field(..., description="The ID of the order that was executed.")
    instrument_id: str = Field(..., description="ID of the financial instrument.")
    side: OrderSide = Field(..., description="Buy or Sell.")
    quantity: float = Field(..., description="The quantity traded.")
    price: float = Field(..., description="The execution price.")
    trade_time: int = Field(..., description="The time of the trade.")