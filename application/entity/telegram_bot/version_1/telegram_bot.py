"""
TelegramBot entity for Telegram bot application.

Represents a Telegram bot instance in the system.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class TelegramBot(CyodaEntity):
    """
    TelegramBot represents a Telegram bot instance in the system.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    """

    ENTITY_NAME: ClassVar[str] = "TelegramBot"
    ENTITY_VERSION: ClassVar[int] = 1

    bot_id: int = Field(..., description="Telegram bot ID")
    bot_name: str = Field(..., description="Bot name")
    bot_token: str = Field(..., description="Bot API token")
    is_active: bool = Field(default=True, description="Whether bot is active")
    description: Optional[str] = Field(
        default=None, description="Bot description"
    )
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when bot was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when bot was last updated",
    )

    @field_validator("bot_id")
    @classmethod
    def validate_bot_id(cls, v: int) -> int:
        """Validate bot_id is positive"""
        if v <= 0:
            raise ValueError("Bot ID must be positive")
        return v

    @field_validator("bot_name")
    @classmethod
    def validate_bot_name(cls, v: str) -> str:
        """Validate bot_name is not empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Bot name must be non-empty")
        return v.strip()

    @field_validator("bot_token")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        """Validate bot_token is not empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Bot token must be non-empty")
        return v.strip()

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

