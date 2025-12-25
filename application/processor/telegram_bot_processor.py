"""
TelegramBotProcessor for Telegram bot application.

Handles business logic for TelegramBot entities.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.telegram_bot import TelegramBot


class TelegramBotProcessor(CyodaProcessor):
    """Processor for TelegramBot entities."""

    def __init__(self) -> None:
        super().__init__(
            name="TelegramBotProcessor",
            description="Processes TelegramBot entities",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the TelegramBot entity.

        Args:
            entity: The TelegramBot to process
            **kwargs: Additional processing parameters

        Returns:
            The processed entity
        """
        try:
            self.logger.info(
                f"Processing TelegramBot {getattr(entity, 'technical_id', '<unknown>')}"
            )

            telegram_bot = cast_entity(entity, TelegramBot)

            self.logger.info(
                f"TelegramBot {telegram_bot.technical_id} processed successfully"
            )

            return telegram_bot

        except Exception as e:
            self.logger.error(
                f"Error processing entity {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

