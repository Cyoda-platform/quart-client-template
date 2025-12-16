from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity

class RiskLimitProfile(CyodaEntity):
    """Defines a profile for risk limits and parameters."""
    
    ENTITY_NAME: str = "RiskLimitProfile"
    ENTITY_VERSION: int = 1
    
    profile_id: str = Field(..., description="Unique business identifier for the risk limit profile")
    name: str = Field(..., description="Name of the risk limit profile")
    description: str = Field(..., description="Detailed description of the risk limit profile")
    max_loss_percentage: float = Field(..., description="Maximum allowed loss as a percentage of capital")
    max_drawdown_amount: float = Field(..., description="Maximum allowed drawdown amount")
    leverage_limit: float = Field(..., description="Maximum allowed leverage")
    enabled: bool = Field(..., description="Flag indicating if the profile is active")
