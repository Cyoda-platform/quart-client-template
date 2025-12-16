from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class LimitRule(CyodaEntity):
    """
    LimitRule defines trading limits for accounts and instruments.

    Enforces compliance and risk management constraints.
    """

    ENTITY_NAME: ClassVar[str] = "LimitRule"
    ENTITY_VERSION: ClassVar[int] = 1

    rule_id: str = Field(..., description="Business identifier for the limit rule")
    account_id: str = Field(..., description="Account the rule applies to")
    instrument_id: Optional[str] = Field(
        None, description="Specific instrument (null for all)"
    )
    limit_type: str = Field(
        ..., description="Type of limit: NOTIONAL, QUANTITY, LOSS, etc."
    )
    value: float = Field(..., description="Limit value")
    active: bool = Field(default=True, description="Whether the rule is active")
    status: str = Field(default="Active", description="Rule status")

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
