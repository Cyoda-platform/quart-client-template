"""
Subscriber entity for the newsletter application.

Represents a user subscribed to the weekly cat-fact newsletter.
Manages subscription state and email information.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Subscriber(CyodaEntity):
    """
    Subscriber represents a user subscribed to the newsletter.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> active -> unsubscribed
    """

    ENTITY_NAME: ClassVar[str] = "Subscriber"
    ENTITY_VERSION: ClassVar[int] = 1

    email: str = Field(..., description="Email address of the subscriber")
    subscribed_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="subscribedAt",
        description="Timestamp when subscriber signed up (ISO 8601 format)",
    )
    unsubscribed_at: Optional[str] = Field(
        default=None,
        alias="unsubscribedAt",
        description="Timestamp when subscriber unsubscribed (ISO 8601 format)",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email must be non-empty")
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email must be a valid email address")
        return v.strip().lower()

    def is_active(self) -> bool:
        """Check if subscriber is currently active"""
        return self.state == "active"

    def is_unsubscribed(self) -> bool:
        """Check if subscriber has unsubscribed"""
        return self.state == "unsubscribed"

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
