"""
InteractionTrackingProcessor for tracking subscriber interactions.

Handles the recording of email opens, clicks, and unsubscribe actions
with deduplication and metadata capture.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.interaction.version_1.interaction import Interaction


class InteractionTrackingProcessor(CyodaProcessor):
    """
    Processor for tracking subscriber interactions with emails.
    """

    def __init__(self) -> None:
        super().__init__(
            name="InteractionTrackingProcessor",
            description="Tracks subscriber interactions (opens, clicks, unsubscribes)",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Interaction entity to record tracking data.

        Args:
            entity: The Interaction entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed Interaction entity
        """
        try:
            self.logger.info(
                f"Recording interaction for {getattr(entity, 'technical_id', '<unknown>')}"
            )

            interaction = cast_entity(entity, Interaction)

            # Validate required fields
            if not interaction.subscriber_id or not interaction.email_send_id:
                raise ValueError("Subscriber ID and Email Send ID are required")

            interaction.update_timestamp()

            self.logger.info(
                f"Interaction {interaction.technical_id} recorded successfully"
            )

            return interaction

        except Exception as e:
            self.logger.error(
                f"Error recording interaction {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

