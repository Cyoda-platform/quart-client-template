"""
Subscriber entity for Weekly Cat Fact Subscription application.

Represents a subscriber to the weekly cat fact email service.
Manages subscription status, email information, and unsubscribe tokens.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Subscriber(CyodaEntity):
    """
    Subscriber represents a user subscribed to the weekly cat fact service.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> active -> unsubscribed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Subscriber"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    email: str = Field(..., description="Email address of the subscriber")
    name: Optional[str] = Field(
        default=None, description="Optional name of the subscriber"
    )
    subscribed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="subscribedAt",
        description="Timestamp when subscriber joined (ISO 8601 format)",
    )
    status: str = Field(
        default="active",
        description="Subscription status: active or unsubscribed",
    )
    unsubscribe_token: str = Field(
        ...,
        alias="unsubscribeToken",
        description="Unique token for unsubscribe link",
    )
    encrypted_email: bool = Field(
        default=True,
        alias="encryptedEmail",
        description="Flag indicating if email is stored encrypted",
    )
    source: str = Field(
        default="web",
        description="Source of subscription: web, import, api, etc.",
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
    ALLOWED_STATUSES: ClassVar[list[str]] = ["active", "unsubscribed"]
    ALLOWED_SOURCES: ClassVar[list[str]] = ["web", "import", "api", "manual"]

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email must be non-empty")
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email must be a valid email address")
        return v.strip().lower()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate name field if provided"""
        if v is None:
            return v
        if len(v.strip()) == 0:
            return None
        if len(v) > 100:
            raise ValueError("Name must be at most 100 characters long")
        return v.strip()

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status field"""
        if v not in cls.ALLOWED_STATUSES:
            raise ValueError(f"Status must be one of: {cls.ALLOWED_STATUSES}")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """Validate source field"""
        if v not in cls.ALLOWED_SOURCES:
            raise ValueError(f"Source must be one of: {cls.ALLOWED_SOURCES}")
        return v

    @field_validator("unsubscribe_token")
    @classmethod
    def validate_unsubscribe_token(cls, v: str) -> str:
        """Validate unsubscribe token is non-empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Unsubscribe token must be non-empty")
        return v.strip()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
