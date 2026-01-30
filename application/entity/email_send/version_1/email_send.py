"""
EmailSend (SendReport) entity for Weekly Cat Fact Subscription application.

Represents an email send operation for a cat fact to subscribers.
Tracks scheduling, delivery status, and success/failure metrics.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class EmailSend(CyodaEntity):
    """
    EmailSend represents a scheduled or completed email send operation.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> pending -> in_progress -> completed/failed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "EmailSend"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    catfact_id: str = Field(
        ..., alias="catfactId", description="Reference to the CatFact entity"
    )
    scheduled_for: str = Field(
        ...,
        alias="scheduledFor",
        description="Timestamp when send is scheduled (ISO 8601 format)",
    )
    sent_at: Optional[str] = Field(
        default=None,
        alias="sentAt",
        description="Timestamp when send completed (ISO 8601 format)",
    )
    total_recipients: int = Field(
        default=0,
        alias="totalRecipients",
        description="Total number of recipients for this send",
    )
    success_count: int = Field(
        default=0,
        alias="successCount",
        description="Number of successfully sent emails",
    )
    failure_count: int = Field(
        default=0,
        alias="failureCount",
        description="Number of failed email sends",
    )
    status: str = Field(
        default="pending",
        description="Send status: pending, in_progress, completed, failed",
    )
    error_details: Optional[str] = Field(
        default=None,
        alias="errorDetails",
        description="Details about any errors that occurred during send",
    )

    # Timestamps
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when the entity was created (ISO 8601 format)",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when the entity was last updated (ISO 8601 format)",
    )

    # Allowed values
    ALLOWED_STATUSES: ClassVar[list[str]] = [
        "pending",
        "in_progress",
        "completed",
        "failed",
    ]

    @field_validator("catfact_id")
    @classmethod
    def validate_catfact_id(cls, v: str) -> str:
        """Validate catfact_id is non-empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("CatFact ID must be non-empty")
        return v.strip()

    @field_validator("scheduled_for")
    @classmethod
    def validate_scheduled_for(cls, v: str) -> str:
        """Validate scheduled_for timestamp"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Scheduled for timestamp must be non-empty")
        return v.strip()

    @field_validator("total_recipients", "success_count", "failure_count")
    @classmethod
    def validate_counts(cls, v: int) -> int:
        """Validate count fields are non-negative"""
        if v < 0:
            raise ValueError("Count must be non-negative")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status field"""
        if v not in cls.ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of: {cls.ALLOWED_STATUSES}")
        return v

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

