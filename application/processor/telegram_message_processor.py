"""
TelegramMessageProcessor for Telegram bot application.

Handles business logic for TelegramMessage entities.
"""

import logging
from typing import Any

from application.entity.telegram_message.version_1.telegram_message import (
    TelegramMessage,
)
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class TelegramMessageProcessor(CyodaProcessor):
    """Processor for TelegramMessage entities."""

    def __init__(self) -> None:
        super().__init__(
            name="TelegramMessageProcessor",
            description="Processes TelegramMessage entities",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the TelegramMessage entity.

        Args:
            entity: The TelegramMessage to process
            **kwargs: Additional processing parameters

        Returns:
            The processed entity
        """
        try:
            self.logger.info(
                f"Processing TelegramMessage {getattr(entity, 'technical_id', '<unknown>')}"
            )

            telegram_message = cast_entity(entity, TelegramMessage)

            self.logger.info(
                f"TelegramMessage {telegram_message.technical_id} processed successfully"
            )

            return telegram_message

        except Exception as e:
            self.logger.error(
                f"Error processing entity {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
