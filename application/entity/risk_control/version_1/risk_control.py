from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class RiskControl(CyodaEntity):
    """
    RiskControl represents risk limits and compliance rules for an account.
    State transitions: initial_state -> active -> breached/suspended
    """

    ENTITY_NAME: ClassVar[str] = "RiskControl"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., description="Account ID")
    rule_type: str = Field(..., description="Rule type: POSITION_LIMIT, LOSS_LIMIT, CONCENTRATION")
    rule_name: str = Field(..., description="Human-readable rule name")
    limit_value: float = Field(..., ge=0, description="Limit threshold")
    current_value: float = Field(default=0, description="Current value against limit")
    is_active: bool = Field(default=True, description="Rule is active")
    breach_action: str = Field(default="ALERT", description="Action on breach: ALERT, BLOCK, SUSPEND")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="Rule creation timestamp"
    )
    updated_at: Optional[str] = Field(None, description="Last update timestamp")

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        if v not in ["POSITION_LIMIT", "LOSS_LIMIT", "CONCENTRATION"]:
            raise ValueError("rule_type must be POSITION_LIMIT, LOSS_LIMIT, or CONCENTRATION")
        return v

    @field_validator("breach_action")
    @classmethod
    def validate_breach_action(cls, v: str) -> str:
        if v not in ["ALERT", "BLOCK", "SUSPEND"]:
            raise ValueError("breach_action must be ALERT, BLOCK, or SUSPEND")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

