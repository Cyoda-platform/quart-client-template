"""
TelegramUser entity for Telegram bot application.

Represents a Telegram user in the system.
"""

from datetime import datetime, timezone
from typing import ClassVar, Optional

from pydantic import ConfigDict, Field, field_validator

from common.entity.cyoda_entity import CyodaEntity


class TelegramUser(CyodaEntity):
    """
    TelegramUser represents a Telegram user in the system.

    Inherits from CyodaEntity to get common fields like entity_id, state, etc.
    """

    ENTITY_NAME: ClassVar[str] = "TelegramUser"
    ENTITY_VERSION: ClassVar[int] = 1

    telegram_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(
        default=None, description="Telegram username"
    )
    first_name: str = Field(..., description="User's first name")
    last_name: Optional[str] = Field(
        default=None, description="User's last name"
    )
    is_bot: bool = Field(default=False, description="Whether user is a bot")
    is_active: bool = Field(default=True, description="Whether user is active")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        alias="createdAt",
        description="Timestamp when user was created",
    )
    updated_at: Optional[str] = Field(
        default=None,
        alias="updatedAt",
        description="Timestamp when user was last updated",
    )

    @field_validator("telegram_id")
    @classmethod
    def validate_telegram_id(cls, v: int) -> int:
        """Validate telegram_id is positive"""
        if v <= 0:
            raise ValueError("Telegram ID must be positive")
        return v

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        """Validate first_name is not empty"""
        if not v or len(v.strip()) == 0:
            raise ValueError("First name must be non-empty")
        return v.strip()

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        validate_assignment=True,
        extra="allow",
    )

