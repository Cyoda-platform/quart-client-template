from typing import ClassVar

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class RiskProfile(CyodaEntity):
    """
    RiskProfile defines risk limits and requirements for an account.

    Manages margin requirements and position limits.
    """

    ENTITY_NAME: ClassVar[str] = "RiskProfile"
    ENTITY_VERSION: ClassVar[int] = 1

    risk_profile_id: str = Field(
        ..., description="Business identifier for the risk profile"
    )
    account_id: str = Field(..., description="Associated account ID")
    max_notional: float = Field(..., description="Maximum notional exposure")
    max_position: float = Field(..., description="Maximum position size")
    margin_requirement: float = Field(..., description="Margin requirement percentage")
    status: str = Field(default="Active", description="Risk profile status")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
