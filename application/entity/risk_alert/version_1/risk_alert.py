from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class RiskAlert(CyodaEntity):
    """
    RiskAlert represents a risk control alert in the trading platform.

    Manages alert lifecycle: initial_state -> created -> triggered -> resolved
    """

    ENTITY_NAME: ClassVar[str] = "RiskAlert"
    ENTITY_VERSION: ClassVar[int] = 1

    alert_type: str = Field(..., alias="alertType", description="Alert type")
    severity: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW")
    account: str = Field(..., description="Affected account")
    order_id: Optional[str] = Field(
        default=None, alias="orderId", description="Related order ID"
    )

    rule_name: str = Field(..., alias="ruleName", description="Triggered rule name")
    rule_description: Optional[str] = Field(
        default=None, alias="ruleDescription", description="Rule description"
    )

    current_value: Optional[float] = Field(
        default=None, alias="currentValue", description="Current metric value"
    )
    threshold_value: Optional[float] = Field(
        default=None, alias="thresholdValue", description="Threshold value"
    )

    message: str = Field(..., description="Alert message")
    action_required: Optional[str] = Field(
        default=None, alias="actionRequired", description="Required action"
    )

    triggered_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="triggeredAt",
        description="Alert trigger timestamp",
    )
    resolved_at: Optional[str] = Field(
        default=None, alias="resolvedAt", description="Alert resolution timestamp"
    )

    status: Optional[str] = Field(
        default=None, description="Alert status (ACTIVE, RESOLVED, ACKNOWLEDGED)"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        if v not in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            raise ValueError("Severity must be CRITICAL, HIGH, MEDIUM, or LOW")
        return v

    def to_api_response(self) -> Dict[str, Any]:
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        return data

