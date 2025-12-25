"""
TelegramUserProcessor for Telegram bot application.

Handles business logic for TelegramUser entities.
"""

import logging
from typing import Any

from application.entity.telegram_user.version_1.telegram_user import TelegramUser
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class TelegramUserProcessor(CyodaProcessor):
    """Processor for TelegramUser entities."""

    def __init__(self) -> None:
        super().__init__(
            name="TelegramUserProcessor",
            description="Processes TelegramUser entities",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the TelegramUser entity.

        Args:
            entity: The TelegramUser to process
            **kwargs: Additional processing parameters

        Returns:
            The processed entity
        """
        try:
            self.logger.info(
                f"Processing TelegramUser {getattr(entity, 'technical_id', '<unknown>')}"
            )

            telegram_user = cast_entity(entity, TelegramUser)

            self.logger.info(
                f"TelegramUser {telegram_user.technical_id} processed successfully"
            )

            return telegram_user

        except Exception as e:
            self.logger.error(
                f"Error processing entity {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
