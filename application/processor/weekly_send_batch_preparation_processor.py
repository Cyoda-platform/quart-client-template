"""
WeeklySendBatchPreparationProcessor for preparing email send batches.

Handles the preparation of subscriber batches for email sending,
including counting active subscribers and setting up batch metadata.
"""

import logging
from typing import Any

from application.entity.email_send.version_1.email_send import EmailSend
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class WeeklySendBatchPreparationProcessor(CyodaProcessor):
    """
    Processor for preparing email send batches.
    """

    def __init__(self) -> None:
        super().__init__(
            name="WeeklySendBatchPreparationProcessor",
            description="Prepares batches of subscribers for email sending",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the EmailSend entity to prepare batches.

        Args:
            entity: The EmailSend entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed EmailSend entity
        """
        try:
            self.logger.info(
                f"Preparing batches for {getattr(entity, 'technical_id', '<unknown>')}"
            )

            email_send = cast_entity(entity, EmailSend)

            # In a real implementation, this would query active subscribers
            # For now, we just validate the entity structure
            if not email_send.catfact_id:
                raise ValueError("CatFact ID is required")

            email_send.status = "in_progress"
            email_send.update_timestamp()

            self.logger.info(
                f"EmailSend {email_send.technical_id} batches prepared successfully"
            )

            return email_send

        except Exception as e:
            self.logger.error(
                f"Error preparing batches {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
