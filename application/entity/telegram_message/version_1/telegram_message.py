"""
TelegramMessage entity for Telegram bot application.

Represents a message in the Telegram bot system.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class TelegramMessage(CyodaEntity):
    """
    TelegramMessage represents a message in the Telegram bot system.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    """

    ENTITY_NAME: ClassVar[str] = "TelegramMessage"
    ENTITY_VERSION: ClassVar[int] = 1

    message_id: int = Field(..., description="Telegram message ID")
    chat_id: int = Field(..., description="Telegram chat ID")
    user_id: int = Field(..., description="Telegram user ID who sent the message")
    text: str = Field(..., description="Message text content")
    is_processed: bool = Field(
        default=False, description="Whether message has been processed"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when message was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when message was last updated",
    )

    @field_validator("message_id")
    @classmethod
    def validate_message_id(cls, v: int) -> int:
        """Validate message_id is positive"""
        if v <= 0:
            raise ValueError("Message ID must be positive")
        return v

    @field_validator("chat_id")
    @classmethod
    def validate_chat_id(cls, v: int) -> int:
        """Validate chat_id is not zero"""
        if v == 0:
            raise ValueError("Chat ID cannot be zero")
        return v

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: int) -> int:
        """Validate user_id is positive"""
        if v <= 0:
            raise ValueError("User ID must be positive")
        return v

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """Validate text is not empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Message text must be non-empty")
        return v.strip()

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

