"""
SubscriberProcessor for email subscriber activation.

Handles subscriber activation and report tracking.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.subscriber import Subscriber
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor

logger = logging.getLogger(__name__)


class SubscriberProcessor(CyodaProcessor):
    """Processor for subscriber activation and initialization."""

    def __init__(self) -> None:
        super().__init__(
            name="SubscriberProcessor",
            description="Activates subscriber and initializes report tracking",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process Subscriber entity by activating and initializing.

        Args:
            entity: The Subscriber entity to process
            **kwargs: Additional processing parameters

        Returns:
            Updated Subscriber entity
        """
        try:
            subscriber = cast_entity(entity, Subscriber)
            logger.info(f"Processing Subscriber {subscriber.technical_id}")

            # Initialize subscriber
            if subscriber.is_active is None:
                subscriber.is_active = True

            if subscriber.report_count is None:
                subscriber.report_count = 0

            if subscriber.subscribed_at is None:
                subscriber.subscribed_at = (
                    datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                )

            subscriber.update_timestamp()

            logger.info(
                f"Activated subscriber {subscriber.technical_id}: {subscriber.email}"
            )

            return subscriber

        except Exception as e:
            logger.exception(f"Error processing Subscriber: {str(e)}")
            return entity
