"""
TelegramBotValidationCriterion for Telegram bot application.

Validates TelegramBot entities.
"""

from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.telegram_bot.version_1.telegram_bot import TelegramBot


class TelegramBotValidationCriterion(CyodaCriteriaChecker):
    """Criterion for validating TelegramBot entities."""

    def __init__(self) -> None:
        super().__init__(
            name="TelegramBotValidationCriterion",
            description="Validates TelegramBot entities",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if TelegramBot is valid.

        Args:
            entity: The TelegramBot to validate
            **kwargs: Additional parameters

        Returns:
            True if valid, False otherwise
        """
        try:
            telegram_bot = cast_entity(entity, TelegramBot)

            if not telegram_bot.bot_id or telegram_bot.bot_id <= 0:
                return False

            if not telegram_bot.bot_name:
                return False

            if not telegram_bot.bot_token:
                return False

            return True

        except Exception:
            return False
