"""
TelegramMessageValidationCriterion for Telegram bot application.

Validates TelegramMessage entities.
"""

from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.telegram_message.version_1.telegram_message import (
    TelegramMessage,
)


class TelegramMessageValidationCriterion(CyodaCriteriaChecker):
    """Criterion for validating TelegramMessage entities."""

    def __init__(self) -> None:
        super().__init__(
            name="TelegramMessageValidationCriterion",
            description="Validates TelegramMessage entities",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if TelegramMessage is valid.

        Args:
            entity: The TelegramMessage to validate
            **kwargs: Additional parameters

        Returns:
            True if valid, False otherwise
        """
        try:
            telegram_message = cast_entity(entity, TelegramMessage)

            if not telegram_message.message_id or telegram_message.message_id <= 0:
                return False

            if telegram_message.chat_id == 0:
                return False

            if not telegram_message.user_id or telegram_message.user_id <= 0:
                return False

            if not telegram_message.text:
                return False

            return True

        except Exception:
            return False
