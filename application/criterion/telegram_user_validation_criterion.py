"""
TelegramUserValidationCriterion for Telegram bot application.

Validates TelegramUser entities.
"""

from typing import Any

from common.processor.base import CyodaEntity, CyodaCriterion
from application.entity.telegram_user import TelegramUser


class TelegramUserValidationCriterion(CyodaCriterion):
    """Criterion for validating TelegramUser entities."""

    def __init__(self) -> None:
        super().__init__(
            name="TelegramUserValidationCriterion",
            description="Validates TelegramUser entities",
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Evaluate if TelegramUser is valid.

        Args:
            entity: The TelegramUser to validate
            **kwargs: Additional parameters

        Returns:
            True if valid, False otherwise
        """
        try:
            telegram_user = entity
            if not isinstance(telegram_user, TelegramUser):
                return False

            if not telegram_user.telegram_id or telegram_user.telegram_id <= 0:
                return False

            if not telegram_user.first_name:
                return False

            return True

        except Exception:
            return False
