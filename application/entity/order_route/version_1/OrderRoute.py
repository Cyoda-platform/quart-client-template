from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity

class OrderRoute(CyodaEntity):
    """Defines a route for placing orders to a specific market venue."""
    
    ENTITY_NAME: str = "OrderRoute"
    ENTITY_VERSION: int = 1
    
    route_id: str = Field(..., description="Unique business identifier for the order route")
    name: str = Field(..., description="Name of the order route")
    market_venue_id: str = Field(..., description="Identifier of the market venue this route connects to")
    priority: int = Field(..., description="Priority of this route for order execution")
    commission_rate: float = Field(..., description="Commission rate associated with using this route")
    enabled: bool = Field(..., description="Flag indicating if the route is active")
