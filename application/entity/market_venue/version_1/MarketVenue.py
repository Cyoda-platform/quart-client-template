from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity

class MarketVenue(CyodaEntity):
    """Represents a market venue where trades can occur."""
    
    ENTITY_NAME: str = "MarketVenue"
    ENTITY_VERSION: int = 1
    
    venue_id: str = Field(..., description="Unique business identifier for the market venue")
    name: str = Field(..., description="Name of the market venue")
    country: str = Field(..., description="Country where the market venue is located")
    currency: str = Field(..., description="Primary currency traded on the venue")
    operating_hours: str = Field(..., description="Operating hours of the venue (e.g., '09:00-17:00')")
