"""
AuditEvent entity for trading platform.

Represents an audit event that tracks important actions and state changes
across the trading system for compliance, debugging, and monitoring purposes.
"""

from typing import ClassVar, Optional

from pydantic import ConfigDict, Field

from common.entity.cyoda_entity import CyodaEntity


class AuditEvent(CyodaEntity):
    """
    AuditEvent entity representing an auditable event in the system.

    Captures events such as order submissions, fills, position changes,
    and other important actions for compliance and audit trail purposes.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "AuditEvent"
    ENTITY_VERSION: ClassVar[int] = 1

    # Core audit event fields
    event_type: str = Field(
        ...,
        alias="eventType",
        description="Type of event (e.g., ORDER_SUBMITTED, FILL_RECEIVED)",
    )
    entity_type: str = Field(
        ...,
        alias="entityType",
        description="Type of entity involved (e.g., Order, Fill, Position)",
    )
    entity_id: str = Field(
        ..., alias="entityId", description="Identifier of the entity involved"
    )
    actor: str = Field(
        ..., description="User or system component that triggered the event"
    )
    timestamp: str = Field(..., description="Timestamp of the event (ISO 8601)")

    # Optional fields
    details: Optional[dict] = Field(
        default=None, description="Additional event details as key-value pairs"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
