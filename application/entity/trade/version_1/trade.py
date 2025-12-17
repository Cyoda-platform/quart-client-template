from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity
import datetime
from enum import Enum

class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class Trade(CyodaEntity):
    """
    Represents an executed order or a partial fill of an order.
    """

    # Constants
    ENTITY_NAME: str = "Trade"
    ENTITY_VERSION: int = 1

    # Business ID
    trade_id: str = Field(..., description="Unique identifier for the trade.", example="TRD-2025-12-15-00001")

    # Trade Fields
    order_id: str = Field(..., description="The order that this trade is part of.", example="ORD-2025-12-15-00001")
    portfolio_id: str = Field(..., description="The portfolio this trade belongs to.", example="PORT-001")
    instrument_id: str = Field(..., description="Identifier for the financial instrument.", example="AAPL")
    side: TradeSide = Field(..., description="Side of the trade (BUY or SELL).")
    quantity: int = Field(..., description="The number of units traded.", example=50)
    price: float = Field(..., description="The price at which the trade was executed.", example=145.12)
    execution_timestamp: datetime.datetime = Field(..., description="Timestamp of when the trade was executed.")
