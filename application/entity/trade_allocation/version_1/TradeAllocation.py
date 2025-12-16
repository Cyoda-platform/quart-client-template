from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity

class TradeAllocation(CyodaEntity):
    """Represents an allocation of a trade to an account."""
    
    ENTITY_NAME: str = "TradeAllocation"
    ENTITY_VERSION: int = 1
    
    allocation_id: str = Field(..., description="Unique business identifier for the trade allocation")
    execution_report_id: str = Field(..., description="Identifier of the execution report this allocation belongs to")
    account_id: str = Field(..., description="Identifier of the account to which the trade was allocated")
    allocated_quantity: float = Field(..., description="Quantity allocated to this account")
    allocation_price: float = Field(..., description="Price at which the quantity was allocated")
    allocation_time: str = Field(..., description="Timestamp of the allocation (ISO 8601 format)")
