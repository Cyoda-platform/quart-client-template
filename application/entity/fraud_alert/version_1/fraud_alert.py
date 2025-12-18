from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class FraudAlert(CyodaEntity):
    ENTITY_NAME: ClassVar[str] = "FraudAlert"
    ENTITY_VERSION: ClassVar[int] = 1

    merchant_id: str = Field(..., description="Merchant identifier")
    payment_id: str = Field(..., description="Related payment identifier")
    customer_id: str = Field(..., description="Customer identifier")

    fraud_score: float = Field(..., ge=0.0, le=100.0, description="Fraud risk score")
    fraud_reason: str = Field(..., description="Primary fraud detection reason")

    fraud_signals: Dict[str, Any] = Field(
        default_factory=dict, description="Detailed fraud signals and scores"
    )

    alert_type: str = Field(
        default="auto", description="Alert type: auto, manual, escalated"
    )
    alert_status: str = Field(
        default="open", description="Status: open, reviewed, resolved, false_positive"
    )

    recommended_action: str = Field(
        default="REVIEW", description="Recommended action: ALLOW, REVIEW, DECLINE"
    )
    actual_action: Optional[str] = Field(
        default=None, description="Action actually taken"
    )

    analyst_notes: Optional[str] = Field(
        default=None, description="Fraud analyst review notes"
    )
    analyst_id: Optional[str] = Field(
        default=None, description="Analyst who reviewed the alert"
    )

    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Alert creation timestamp",
    )
    reviewed_at: Optional[str] = Field(default=None, description="Review timestamp")

    @field_validator("alert_type")
    @classmethod
    def validate_alert_type(cls, v: str) -> str:
        if v not in ["auto", "manual", "escalated"]:
            raise ValueError("alert_type must be auto, manual, or escalated")
        return v

    @field_validator("alert_status")
    @classmethod
    def validate_alert_status(cls, v: str) -> str:
        if v not in ["open", "reviewed", "resolved", "false_positive"]:
            raise ValueError(
                "alert_status must be open, reviewed, resolved, or false_positive"
            )
        return v

    @field_validator("recommended_action", "actual_action")
    @classmethod
    def validate_action(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ["ALLOW", "REVIEW", "DECLINE"]:
            raise ValueError("Action must be ALLOW, REVIEW, or DECLINE")
        return v

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
