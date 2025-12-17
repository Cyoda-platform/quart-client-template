from pydantic import Field, BaseModel
from common.entity.cyoda_entity import CyodaEntity
import datetime

class MarketData(CyodaEntity):
    """
    Represents real-time market information for a financial instrument.
    """

    # Constants
    ENTITY_NAME: str = "MarketData"
    ENTITY_VERSION: int = 1

    # Business ID
    instrument_id: str = Field(..., description="Unique identifier for the financial instrument (e.g., Ticker, ISIN).", example="AAPL")

    # Market Data Fields
    last_price: float | None = Field(None, description="The price of the last trade.", example=145.12)
    bid_price: float = Field(..., description="The best available price at which a buyer is willing to buy.", example=145.10)
    ask_price: float = Field(..., description="The best available price at which a seller is willing to sell.", example=145.14)
    bid_size: int = Field(..., description="The number of shares available at the bid price.", example=500)
    ask_size: int = Field(..., description="The number of shares available at the ask price.", example=700)
    volume: int = Field(..., description="The total number of shares traded during the period.", example=15000000)
    timestamp: datetime.datetime = Field(..., description="The timestamp of when the market data was captured.")
