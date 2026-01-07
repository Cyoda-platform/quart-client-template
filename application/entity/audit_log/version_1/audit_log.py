"""
AuditLog Entity for Enterprise Payment Processing System

Represents an audit log entry for comprehensive audit trail tracking.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class AuditLog(CyodaEntity):
    """
    AuditLog represents an audit log entry for tracking system activities.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> created -> recorded
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "AuditLog"
    ENTITY_VERSION: ClassVar[int] = 1

    # Audit log fields
    log_id: str = Field(..., description="Unique audit log ID")
    event_type: str = Field(..., description="Type of event (e.g., TRANSACTION_CREATED, FRAUD_CHECK)")
    entity_type: str = Field(..., description="Type of entity affected (e.g., PaymentTransaction, Settlement)")
    entity_id: str = Field(..., description="ID of the entity affected")
    action: str = Field(..., description="Action performed (CREATE, UPDATE, DELETE, VALIDATE, etc.)")

    # User/system information
    actor: str = Field(..., description="User or system that performed the action")
    actor_type: str = Field(..., description="Type of actor (USER, SYSTEM, PROCESSOR)")

    # Change details
    old_values: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="oldValues",
        description="Previous values before the change",
    )
    new_values: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="newValues",
        description="New values after the change",
    )
    changes_summary: Optional[str] = Field(
        default=None,
        alias="changesSummary",
        description="Summary of changes made",
    )

    # Status and result
    status: Optional[str] = Field(
        default=None,
        description="Status of the action (SUCCESS, FAILURE, PENDING)",
    )
    result_message: Optional[str] = Field(
        default=None,
        alias="resultMessage",
        description="Result message or error details",
    )

    # Timestamps
    timestamp: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        description="Timestamp when the event occurred",
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when audit log was created",
    )

    # Additional context
    ip_address: Optional[str] = Field(
        default=None,
        alias="ipAddress",
        description="IP address of the actor",
    )
    session_id: Optional[str] = Field(
        default=None,
        alias="sessionId",
        description="Session ID for tracking user sessions",
    )

    # Validation rules
    ALLOWED_EVENT_TYPES: ClassVar[List[str]] = [
        "TRANSACTION_CREATED",
        "TRANSACTION_VALIDATED",
        "FRAUD_CHECK_PERFORMED",
        "SETTLEMENT_CREATED",
        "SETTLEMENT_RECONCILED",
        "AUDIT_LOG_CREATED",
    ]
    ALLOWED_ACTIONS: ClassVar[List[str]] = [
        "CREATE",
        "UPDATE",
        "DELETE",
        "VALIDATE",
        "PROCESS",
        "RECONCILE",
    ]
    ALLOWED_STATUSES: ClassVar[List[str]] = ["SUCCESS", "FAILURE", "PENDING"]

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type"""
        if v not in cls.ALLOWED_EVENT_TYPES:
            raise ValueError(
                f"Event type must be one of: {cls.ALLOWED_EVENT_TYPES}"
            )
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        """Validate action"""
        if v not in cls.ALLOWED_ACTIONS:
            raise ValueError(
                f"Action must be one of: {cls.ALLOWED_ACTIONS}"
            )
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        """Validate status"""
        if v is not None and v not in cls.ALLOWED_STATUSES:
            raise ValueError(
                f"Status must be one of: {cls.ALLOWED_STATUSES}"
            )
        return v

    def to_api_response(self) -> Dict[str, Any]:
        """Convert to API response format"""
        data = self.model_dump(by_alias=True)
        data["state"] = self.state
        return data

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

