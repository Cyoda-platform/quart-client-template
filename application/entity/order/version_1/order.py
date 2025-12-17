from pydantic import Field
from enum import Enum
from common.entity.cyoda_entity import CyodaEntity
from typing import Optional

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class Order(CyodaEntity):
    """
    Represents a client's instruction to buy or sell a financial instrument.
    """
    ENTITY_NAME = "order"
    ENTITY_VERSION = 1

    portfolio_id: str = Field(..., description="The ID of the portfolio.")
    instrument_id: str = Field(..., description="ID of the financial instrument.")
    order_type: OrderType = Field(..., description="Type of the order.")
    side: OrderSide = Field(..., description="Buy or Sell.")
    quantity: float = Field(..., description="The quantity to trade.")
    price: Optional[float] = Field(None, description="The price for Limit and Stop orders.")