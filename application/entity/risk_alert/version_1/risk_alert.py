"""
RiskAlert entity for trading platform.

Represents risk alerts triggered by limit breaches or threshold violations
with escalation and notification workflows.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class RiskAlert(CyodaEntity):
    """
    Represents a risk alert in the trading system.
    
    Manages alert lifecycle: initial_state -> triggered -> notified -> resolved -> archived
    """

    ENTITY_NAME: ClassVar[str] = "RiskAlert"
    ENTITY_VERSION: ClassVar[int] = 1

    account_id: str = Field(..., alias="accountId", description="Account ID")
    alert_type: str = Field(
        ..., alias="alertType", description="LIMIT_BREACH, THRESHOLD_WARNING, ANOMALY"
    )
    severity: str = Field(
        ..., description="CRITICAL, HIGH, MEDIUM, LOW"
    )
    limit_id: Optional[str] = Field(
        default=None, alias="limitId", description="Related RiskLimit ID"
    )
    current_value: float = Field(
        ..., alias="currentValue", description="Current metric value"
    )
    threshold_value: float = Field(
        ..., alias="thresholdValue", description="Threshold that was breached"
    )
    message: str = Field(..., description="Alert message")
    action_taken: Optional[str] = Field(
        default=None, alias="actionTaken", description="Action taken (e.g., BLOCKED)"
    )
    created_at: str = Field(..., alias="createdAt", description="Alert creation time")
    resolved_at: Optional[str] = Field(
        default=None, alias="resolvedAt", description="Resolution time"
    )

    def is_critical(self) -> bool:
        return self.severity == "CRITICAL"

    def is_resolved(self) -> bool:
        return self.state == "resolved"

