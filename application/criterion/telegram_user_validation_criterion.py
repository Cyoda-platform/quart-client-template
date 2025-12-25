"""
TelegramUserValidationCriterion for Telegram bot application.

Validates TelegramUser entities.
"""

from typing import Any

from application.entity.telegram_user.version_1.telegram_user import TelegramUser
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class TelegramUserValidationCriterion(CyodaCriteriaChecker):
    """Criterion for validating TelegramUser entities."""

    def __init__(self) -> None:
        super().__init__(
            name="TelegramUserValidationCriterion",
            description="Validates TelegramUser entities",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if TelegramUser is valid.

        Args:
            entity: The TelegramUser to validate
            **kwargs: Additional parameters

        Returns:
            True if valid, False otherwise
        """
        try:
            telegram_user = cast_entity(entity, TelegramUser)

            if not telegram_user.telegram_id or telegram_user.telegram_id <= 0:
                return False

            if not telegram_user.first_name:
                return False

            return True

        except Exception:
            return False
