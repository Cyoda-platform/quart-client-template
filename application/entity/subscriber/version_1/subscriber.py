"""
Subscriber entity for email report subscriptions.

Represents an email subscriber who receives analysis reports.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import EmailStr, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Subscriber(CyodaEntity):
    """
    Subscriber represents an email subscriber.

    States: initial_state -> created -> active <-> inactive
    """

    ENTITY_NAME: ClassVar[str] = "Subscriber"
    ENTITY_VERSION: ClassVar[int] = 1

    email: EmailStr = Field(..., description="Email address")
    name: Optional[str] = Field(
        default=None,
        description="Subscriber name",
    )
    is_active: Optional[bool] = Field(
        default=True,
        alias="isActive",
        description="Whether subscriber receives reports",
    )
    subscribed_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="subscribedAt",
        description="Timestamp when subscribed",
    )
    last_report_sent: Optional[str] = Field(
        default=None,
        alias="lastReportSent",
        description="Timestamp of last report sent",
    )
    report_count: Optional[int] = Field(
        default=0,
        alias="reportCount",
        description="Number of reports received",
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when last updated",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email is required")
        return v.lower()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

