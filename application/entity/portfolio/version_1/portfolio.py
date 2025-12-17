from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity

class Portfolio(CyodaEntity):
    """
    A collection of positions held by a trading entity.
    """
    ENTITY_NAME = "portfolio"
    ENTITY_VERSION = 1

    name: str = Field(..., description="The name of the portfolio.")
    owner_id: str = Field(..., description="The ID of the owner of the portfolio.")