"""
UnsubscribeProcessor for processing subscriber unsubscribe requests.

Handles the unsubscribe workflow by updating subscriber status
and recording the unsubscribe timestamp.
"""

import logging
from typing import Any

from application.entity.subscriber.version_1.subscriber import Subscriber
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class UnsubscribeProcessor(CyodaProcessor):
    """
    Processor for processing unsubscribe requests.
    """

    def __init__(self) -> None:
        super().__init__(
            name="UnsubscribeProcessor",
            description="Processes subscriber unsubscribe requests",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Subscriber entity to unsubscribe.

        Args:
            entity: The Subscriber entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed Subscriber entity
        """
        try:
            self.logger.info(
                f"Processing unsubscribe for {getattr(entity, 'technical_id', '<unknown>')}"
            )

            subscriber = cast_entity(entity, Subscriber)

            # Update status to unsubscribed
            subscriber.status = "unsubscribed"
            subscriber.update_timestamp()

            self.logger.info(
                f"Subscriber {subscriber.technical_id} unsubscribed successfully"
            )

            return subscriber

        except Exception as e:
            self.logger.error(
                f"Error processing unsubscribe {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
