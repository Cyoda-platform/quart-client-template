from pydantic import Field
from common.entity.cyoda_entity import CyodaEntity

class Account(CyodaEntity):
    """Represents a financial account."""
    
    ENTITY_NAME: str = "Account"
    ENTITY_VERSION: int = 1
    
    account_id: str = Field(..., description="Unique business identifier for the account")
    name: str = Field(..., description="Human-readable name for the account")
    currency: str = Field(..., description="Currency of the account (e.g., USD, EUR)")
    balance: float = Field(..., description="Current balance of the account")
    status: str = Field(..., description="Current status of the account (e.g., active, closed, pending)")
    created_at: str = Field(..., description="Timestamp when the account was created (ISO 8601 format)")
