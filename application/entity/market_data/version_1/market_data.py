from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity

class MarketData(CyodaEntity):
    """
    Represents real-time market information for a financial instrument.
    """
    ENTITY_NAME = "market_data"
    ENTITY_VERSION = 1

    instrument_id: str = Field(..., description="ID of the financial instrument.")
    last_price: float = Field(..., description="Last trade price.")
    bid_price: float = Field(..., description="Current bid price.")
    ask_price: float = Field(..., description="Current ask price.")
    volume: int = Field(..., description="Trading volume.")
    timestamp: int = Field(..., description="Timestamp of the data.")