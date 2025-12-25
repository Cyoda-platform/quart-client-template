"""
TelegramBotValidationCriterion for Telegram bot application.

Validates TelegramBot entities.
"""

from typing import Any

from common.processor.base import CyodaEntity, CyodaCriterion
from application.entity.telegram_bot import TelegramBot


class TelegramBotValidationCriterion(CyodaCriterion):
    """Criterion for validating TelegramBot entities."""

    def __init__(self) -> None:
        super().__init__(
            name="TelegramBotValidationCriterion",
            description="Validates TelegramBot entities",
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Evaluate if TelegramBot is valid.

        Args:
            entity: The TelegramBot to validate
            **kwargs: Additional parameters

        Returns:
            True if valid, False otherwise
        """
        try:
            telegram_bot = entity
            if not isinstance(telegram_bot, TelegramBot):
                return False

            if not telegram_bot.bot_id or telegram_bot.bot_id <= 0:
                return False

            if not telegram_bot.bot_name:
                return False

            if not telegram_bot.bot_token:
                return False

            return True

        except Exception:
            return False

