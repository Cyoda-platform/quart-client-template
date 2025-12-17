from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity
import datetime

class Position(CyodaEntity):
    """
    Represents the net holding of a particular financial instrument in a portfolio.
    """

    # Constants
    ENTITY_NAME: str = "Position"
    ENTITY_VERSION: int = 1

    # Business ID (composite)
    position_id: str = Field(..., description="Unique identifier for the position, often a combination of portfolio and instrument.", example="PORT-001_AAPL")

    # Position Fields
    portfolio_id: str = Field(..., description="The portfolio this position belongs to.", example="PORT-001")
    instrument_id: str = Field(..., description="Identifier for the financial instrument.", example="AAPL")
    quantity: int = Field(..., description="The number of units held. Can be negative for short positions.", example=500)
    average_price: float = Field(..., description="The weighted average price of the units held.", example=135.50)
    market_value: float = Field(..., description="The current market value of the position (quantity * last_price).", example=72560.00)
    last_updated: datetime.datetime = Field(..., description="Timestamp of the last update to this position.")
