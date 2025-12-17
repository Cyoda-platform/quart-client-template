from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity
import datetime
from enum import Enum

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

    # Constants
    ENTITY_NAME: str = "Order"
    ENTITY_VERSION: int = 1

    # Business ID
    order_id: str = Field(..., description="Unique identifier for the order.", example="ORD-2025-12-15-00001")

    # Order Fields
    portfolio_id: str = Field(..., description="The portfolio this order belongs to.", example="PORT-001")
    instrument_id: str = Field(..., description="Identifier for the financial instrument.", example="AAPL")
    order_type: OrderType = Field(..., description="Type of the order (MARKET, LIMIT, STOP).")
    side: OrderSide = Field(..., description="Side of the order (BUY or SELL).")
    quantity: int = Field(..., description="The number of units to be traded.", example=100)
    limit_price: float | None = Field(None, description="The limit price for LIMIT or STOP orders.", example=145.00)
    filled_quantity: int = Field(0, description="The number of units that have been filled.", example=0)
    created_at: datetime.datetime = Field(..., description="Timestamp of order creation.")

