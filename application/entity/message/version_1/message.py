"""
Message entity for healthcare application.

Represents a message between patients and healthcare providers with
threading and read status tracking.
"""

from datetime import datetime, timezone
from typing import ClassVar

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class Message(CyodaEntity):
    """
    Message entity representing communication between patients and healthcare providers.
    
    Supports threaded conversations with read status tracking for secure
    healthcare communication.
    """

    # Entity constants
    ENTITY_NAME: ClassVar[str] = "Message"
    ENTITY_VERSION: ClassVar[int] = 1

    # Business ID field
    message_id: str = Field(..., description="Business identifier for the message")

    # Message details
    from_id: str = Field(..., description="ID of the message sender")
    to_id: str = Field(..., description="ID of the message recipient")
    thread_id: str = Field(..., description="ID of the conversation thread")
    content: str = Field(..., description="Message content")
    sent_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="When the message was sent (ISO 8601)"
    )
    read: bool = Field(default=False, description="Whether the message has been read")

    @field_validator("from_id", "to_id", "thread_id")
    @classmethod
    def validate_ids(cls, v: str) -> str:
        """Validate sender, recipient, and thread IDs."""
        if not v or len(v.strip()) == 0:
            raise ValueError("ID must be non-empty")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate message content."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Message content must be non-empty")
        if len(v.strip()) > 5000:
            raise ValueError("Message content must be at most 5000 characters long")
        return v.strip()

    @field_validator("sent_at")
    @classmethod
    def validate_sent_at(cls, v: str) -> str:
        """Validate sent datetime."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Sent at must be non-empty")
        
        try:
            # Parse ISO 8601 datetime
            datetime.fromisoformat(v.strip().replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Sent at must be in ISO 8601 format")
        
        return v.strip()

    def mark_as_read(self) -> None:
        """Mark the message as read."""
        self.read = True

    def mark_as_unread(self) -> None:
        """Mark the message as unread."""
        self.read = False

    def is_recent(self, hours: int = 24) -> bool:
        """Check if message was sent within the specified number of hours."""
        try:
            sent_datetime = datetime.fromisoformat(self.sent_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            hours_diff = (now - sent_datetime).total_seconds() / 3600
            return hours_diff <= hours
        except ValueError:
            return False

    def get_message_age_hours(self) -> float:
        """Get the age of the message in hours."""
        try:
            sent_datetime = datetime.fromisoformat(self.sent_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return (now - sent_datetime).total_seconds() / 3600
        except ValueError:
            return 0.0

    def is_from_patient(self, patient_id: str) -> bool:
        """Check if message is from a specific patient."""
        return self.from_id == patient_id

    def is_to_patient(self, patient_id: str) -> bool:
        """Check if message is to a specific patient."""
        return self.to_id == patient_id

    def involves_patient(self, patient_id: str) -> bool:
        """Check if message involves a specific patient (sender or recipient)."""
        return self.is_from_patient(patient_id) or self.is_to_patient(patient_id)

    def get_content_preview(self, max_length: int = 100) -> str:
        """Get a preview of the message content."""
        if len(self.content) <= max_length:
            return self.content
        return self.content[:max_length].strip() + "..."

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )
