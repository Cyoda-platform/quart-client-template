"""
SubscriptionActivationProcessor for activating new subscriber subscriptions.

Handles the activation of a new subscriber after validation,
including generating unsubscribe tokens and setting status to active.
"""

import logging
import uuid
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.subscriber.version_1.subscriber import Subscriber


class SubscriptionActivationProcessor(CyodaProcessor):
    """
    Processor for activating subscriber subscriptions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="SubscriptionActivationProcessor",
            description="Activates subscriber subscription and generates unsubscribe token",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Subscriber entity to activate subscription.

        Args:
            entity: The Subscriber entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed Subscriber entity
        """
        try:
            self.logger.info(
                f"Activating subscription for {getattr(entity, 'technical_id', '<unknown>')}"
            )

            subscriber = cast_entity(entity, Subscriber)

            # Generate unsubscribe token if not already present
            if not subscriber.unsubscribe_token:
                subscriber.unsubscribe_token = str(uuid.uuid4())

            # Set status to active
            subscriber.status = "active"
            subscriber.update_timestamp()

            self.logger.info(
                f"Subscriber {subscriber.technical_id} activated successfully"
            )

            return subscriber

        except Exception as e:
            self.logger.error(
                f"Error activating subscription {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

