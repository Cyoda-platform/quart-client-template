"""
ComplianceEvent entity for trading platform.

Represents compliance rule violations and trade surveillance events
with immutable audit trail.
"""

from typing import ClassVar, Optional

from pydantic import Field

from common.entity.cyoda_entity import CyodaEntity


class ComplianceEvent(CyodaEntity):
    """
    Represents a compliance event in the trading system.
    
    Manages event lifecycle: initial_state -> detected -> reviewed -> resolved -> archived
    """

    ENTITY_NAME: ClassVar[str] = "ComplianceEvent"
    ENTITY_VERSION: ClassVar[int] = 1

    event_type: str = Field(
        ..., alias="eventType", description="SUSPICIOUS_PATTERN, LIMIT_VIOLATION, REPORTING_REQUIRED"
    )
    account_id: str = Field(..., alias="accountId", description="Account ID")
    rule_id: Optional[str] = Field(
        default=None, alias="ruleId", description="Compliance rule ID"
    )
    rule_name: str = Field(..., alias="ruleName", description="Rule name")
    severity: str = Field(
        ..., description="CRITICAL, HIGH, MEDIUM, LOW"
    )
    description: str = Field(..., description="Event description")
    related_order_id: Optional[str] = Field(
        default=None, alias="relatedOrderId", description="Related order ID"
    )
    related_trade_id: Optional[str] = Field(
        default=None, alias="relatedTradeId", description="Related trade ID"
    )
    evidence: Optional[str] = Field(
        default=None, description="Evidence or details"
    )
    action_required: bool = Field(
        default=False, alias="actionRequired", description="Whether action is required"
    )
    created_at: str = Field(..., alias="createdAt", description="Event creation time")
    resolved_at: Optional[str] = Field(
        default=None, alias="resolvedAt", description="Resolution time"
    )

    def is_critical(self) -> bool:
        return self.severity == "CRITICAL"

    def is_resolved(self) -> bool:
        return self.state == "resolved"

