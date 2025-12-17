from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity

class Position(CyodaEntity):
    """
    Represents the net holding of a particular financial instrument in a portfolio.
    """
    ENTITY_NAME = "position"
    ENTITY_VERSION = "1"

    portfolio_id: str = Field(..., description="The ID of the portfolio.")
    instrument_id: str = Field(..., description="ID of the financial instrument.")
    quantity: float = Field(..., description="The net quantity held.")
    average_price: float = Field(..., description="The average price of the holding.")