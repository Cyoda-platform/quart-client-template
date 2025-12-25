"""
TelegramMessageValidationCriterion for Telegram bot application.

Validates TelegramMessage entities.
"""

from typing import Any

from common.processor.base import CyodaEntity, CyodaCriterion
from application.entity.telegram_message import TelegramMessage


class TelegramMessageValidationCriterion(CyodaCriterion):
    """Criterion for validating TelegramMessage entities."""

    def __init__(self) -> None:
        super().__init__(
            name="TelegramMessageValidationCriterion",
            description="Validates TelegramMessage entities",
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Evaluate if TelegramMessage is valid.

        Args:
            entity: The TelegramMessage to validate
            **kwargs: Additional parameters

        Returns:
            True if valid, False otherwise
        """
        try:
            telegram_message = entity
            if not isinstance(telegram_message, TelegramMessage):
                return False

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

