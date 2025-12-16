from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity

class ExecutionReport(CyodaEntity):
    """Represents a report of a trade execution."""
    
    ENTITY_NAME: str = "ExecutionReport"
    ENTITY_VERSION: int = 1
    
    report_id: str = Field(..., description="Unique business identifier for the execution report")
    order_id: str = Field(..., description="Identifier of the order that was executed")
    execution_time: str = Field(..., description="Timestamp of the execution (ISO 8601 format)")
    symbol: str = Field(..., description="Trading symbol of the instrument executed")
    executed_quantity: float = Field(..., description="Quantity of the instrument executed")
    execution_price: float = Field(..., description="Price at which the instrument was executed")
    side: str = Field(..., description="Side of the trade (e.g., buy, sell)")
    status: str = Field(..., description="Status of the execution (e.g., filled, partially_filled, canceled)")
