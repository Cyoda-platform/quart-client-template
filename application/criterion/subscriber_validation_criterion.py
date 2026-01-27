"""
SubscriberValidationCriterion for validating subscriber email addresses.

Checks that subscriber email is valid before activation.
"""

import logging
from typing import Any

from application.entity.subscriber import Subscriber
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity

logger = logging.getLogger(__name__)


class SubscriberValidationCriterion(CyodaCriteriaChecker):
    """Validation criterion for Subscriber entities."""

    def __init__(self) -> None:
        super().__init__(
            name="SubscriberValidationCriterion",
            description="Validates subscriber email and data",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if Subscriber entity is valid for activation.

        Args:
            entity: The CyodaEntity to validate
            **kwargs: Additional criteria parameters

        Returns:
            True if valid, False otherwise
        """
        try:
            subscriber = cast_entity(entity, Subscriber)
            logger.info(f"Validating Subscriber {subscriber.technical_id}")

            # Check email
            if not subscriber.email or len(subscriber.email.strip()) == 0:
                logger.warning("Email is empty")
                return False

            # Basic email format check
            if "@" not in subscriber.email or "." not in subscriber.email:
                logger.warning(f"Invalid email format: {subscriber.email}")
                return False

            logger.info(f"Validation passed for {subscriber.technical_id}")
            return True

        except Exception as e:
            logger.exception(f"Error validating Subscriber: {str(e)}")
            return False
