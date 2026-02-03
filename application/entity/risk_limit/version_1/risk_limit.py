"""
RiskLimit entity for risk control configuration.

Represents risk limits: initial_state -> configured -> active -> breached
"""

from datetime import datetime, timezone
from typing import ClassVar, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class RiskLimit(CyodaEntity):
    """
    RiskLimit defines risk control thresholds for accounts and positions.
    Manages risk limit lifecycle from configuration through enforcement.
    """

    ENTITY_NAME: ClassVar[str] = "RiskLimit"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    limit_type: str = Field(..., alias="limitType", description="Type: CREDIT, POSITION, NOTIONAL, LOSS")
    limit_value: float = Field(..., alias="limitValue", gt=0, description="Limit threshold")
    current_usage: float = Field(default=0.0, alias="currentUsage", ge=0, description="Current usage")
    currency: str = Field(default="USD", description="Limit currency")
    is_active: bool = Field(default=True, alias="isActive", description="Is limit active")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        alias="createdAt",
        description="Creation timestamp",
    )
    updated_at: Optional[str] = Field(default=None, alias="updatedAt", description="Last update timestamp")

    LIMIT_TYPES: ClassVar[List[str]] = ["CREDIT", "POSITION", "NOTIONAL", "LOSS"]

    @field_validator("limit_type")
    @classmethod
    def validate_limit_type(cls, v: str) -> str:
        if v not in cls.LIMIT_TYPES:
            raise ValueError(f"Limit type must be one of: {cls.LIMIT_TYPES}")
        return v

    model_config = ConfigDict(populate_by_name=True, validate_assignment=True, extra="allow")

