from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity
import datetime

class Portfolio(CyodaEntity):
    """
    A collection of positions held by a trading entity.
    """

    # Constants
    ENTITY_NAME: str = "Portfolio"
    ENTITY_VERSION: int = 1

    # Business ID
    portfolio_id: str = Field(..., description="Unique identifier for the portfolio.", example="PORT-001")

    # Portfolio Fields
    portfolio_name: str = Field(..., description="A human-readable name for the portfolio.", example="Main Trading Account")
    total_value: float = Field(..., description="The total market value of all positions in the portfolio.", example=1500000.00)
    cash_balance: float = Field(..., description="The amount of cash available in the portfolio.", example=250000.00)
    buying_power: float = Field(..., description="The total available capital for placing new trades.", example=500000.00)
    last_rebalanced: datetime.datetime = Field(..., description="Timestamp of when the portfolio was last rebalanced or fully re-evaluated.")

