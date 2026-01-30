"""
Interaction entity for Weekly Cat Fact Subscription application.

Represents a subscriber's interaction with an email send.
Tracks opens, clicks, and unsubscribe actions with metadata.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Interaction(CyodaEntity):
    """
    Interaction represents a subscriber's interaction with a sent email.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    The state field manages workflow states: initial_state -> tracked -> completed
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Interaction"
    ENTITY_VERSION: ClassVar[int] = 1

    # Required fields from functional requirements
    subscriber_id: str = Field(
        ...,
        alias="subscriberId",
        description="Reference to the Subscriber entity",
    )
    email_send_id: str = Field(
        ...,
        alias="emailSendId",
        description="Reference to the EmailSend entity",
    )
    opened_at: Optional[str] = Field(
        default=None,
        alias="openedAt",
        description="Timestamp when email was opened (ISO 8601 format)",
    )
    clicked_at: Optional[str] = Field(
        default=None,
        alias="clickedAt",
        description="Timestamp when a link was clicked (ISO 8601 format)",
    )
    unsubscribe_clicked: bool = Field(
        default=False,
        alias="unsubscribeClicked",
        description="Flag indicating if unsubscribe link was clicked",
    )
    ip_address: Optional[str] = Field(
        default=None,
        alias="ipAddress",
        description="IP address of the interaction",
    )
    user_agent: Optional[str] = Field(
        default=None,
        alias="userAgent",
        description="User agent string from the interaction",
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

    @field_validator("subscriber_id")
    @classmethod
    def validate_subscriber_id(cls, v: str) -> str:
        """Validate subscriber_id is non-empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Subscriber ID must be non-empty")
        return v.strip()

    @field_validator("email_send_id")
    @classmethod
    def validate_email_send_id(cls, v: str) -> str:
        """Validate email_send_id is non-empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Email Send ID must be non-empty")
        return v.strip()

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate IP address format if provided"""
        if v is None:
            return v
        if len(v.strip()) == 0:
            return None
        # Basic IP validation (IPv4 or IPv6)
        if not isinstance(v, str) or len(v) < 7:
            raise ValueError("IP address format is invalid")
        return v.strip()

    @field_validator("user_agent")
    @classmethod
    def validate_user_agent(cls, v: Optional[str]) -> Optional[str]:
        """Validate user agent if provided"""
        if v is None:
            return v
        if len(v.strip()) == 0:
            return None
        if len(v) > 500:
            raise ValueError("User agent must be at most 500 characters long")
        return v.strip()

    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current time"""
        self.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
