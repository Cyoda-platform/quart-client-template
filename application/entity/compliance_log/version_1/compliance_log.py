"""
ComplianceLog entity for institutional trading platform.

Manages immutable audit trail for order decisions and trade events.
Supports MiFID II transaction reporting and OTC derivatives reporting (EMIR/ESAAT).
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class ComplianceLog(CyodaEntity):
    """
    ComplianceLog represents an immutable audit trail entry in the trading system.

    Tracks order decisions, trade events, and regulatory reporting.
    States: logged -> reported -> archived
    """

    ENTITY_NAME: ClassVar[str] = "ComplianceLog"
    ENTITY_VERSION: ClassVar[int] = 1

    # Log identification
    log_id: str = Field(..., alias="logId", description="Unique log entry identifier")

    # Event details
    event_type: str = Field(
        ...,
        alias="eventType",
        description="Event type: order_created, order_filled, trade_captured, etc.",
    )
    entity_type: str = Field(
        ..., alias="entityType", description="Entity type: order, trade, position, etc."
    )
    entity_id: str = Field(..., alias="entityId", description="Related entity ID")

    # Account and legal entity
    account_id: str = Field(..., alias="accountId", description="Trading account ID")
    legal_entity: str = Field(..., alias="legalEntity", description="Legal entity code")

    # Event details
    description: str = Field(..., description="Event description")
    details: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional event details (JSON)"
    )

    # Regulatory reporting
    mifid_reportable: bool = Field(
        default=False, alias="mifidReportable", description="MiFID II reportable"
    )
    emir_reportable: bool = Field(
        default=False, alias="emirReportable", description="EMIR/ESAAT reportable"
    )
    report_status: str = Field(
        default="pending",
        alias="reportStatus",
        description="Report status: pending, reported, archived",
    )

    # Timestamps
    event_timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="eventTimestamp",
        description="Event timestamp (nanosecond precision)",
    )
    reported_at: Optional[str] = Field(
        default=None, alias="reportedAt", description="Reporting timestamp"
    )
    archived_at: Optional[str] = Field(
        default=None, alias="archivedAt", description="Archive timestamp"
    )

    # User and system info
    user_id: Optional[str] = Field(
        default=None, alias="userId", description="User who triggered the event"
    )
    system_id: Optional[str] = Field(
        default=None,
        alias="systemId",
        description="System component that logged the event",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type"""
        valid_types = [
            "order_created",
            "order_submitted",
            "order_filled",
            "order_canceled",
            "order_rejected",
            "trade_captured",
            "trade_enriched",
            "trade_reported",
            "position_opened",
            "position_closed",
            "risk_breach",
            "compliance_check",
        ]
        if v not in valid_types:
            raise ValueError(f"Event type must be one of: {valid_types}")
        return v

    @field_validator("report_status")
    @classmethod
    def validate_report_status(cls, v: str) -> str:
        """Validate report status"""
        valid_statuses = ["pending", "reported", "archived"]
        if v not in valid_statuses:
            raise ValueError(f"Report status must be one of: {valid_statuses}")
        return v

    def is_reported(self) -> bool:
        """Check if event has been reported"""
        return self.report_status == "reported"

    def is_archived(self) -> bool:
        """Check if event has been archived"""
        return self.report_status == "archived"

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
