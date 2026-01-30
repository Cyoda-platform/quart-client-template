"""
SubscriptionValidationCriterion for validating subscriber signups.

Validates that a Subscriber entity has valid email format and required fields
before proceeding to activation.
"""

from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.subscriber.version_1.subscriber import Subscriber


class SubscriptionValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Subscriber entities during signup.
    """

    def __init__(self) -> None:
        super().__init__(
            name="SubscriptionValidationCriterion",
            description="Validates Subscriber signup data",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the Subscriber entity is valid for activation.

        Args:
            entity: The CyodaEntity to validate (expected to be Subscriber)
            **kwargs: Additional criteria parameters

        Returns:
            True if the entity is valid, False otherwise
        """
        try:
            self.logger.info(
                f"Validating entity {getattr(entity, 'technical_id', '<unknown>')}"
            )

            subscriber = cast_entity(entity, Subscriber)

            # Validate email format
            if not subscriber.email or "@" not in subscriber.email:
                self.logger.warning(
                    f"Entity {subscriber.technical_id} has invalid email"
                )
                return False

            # Validate status
            if subscriber.status not in subscriber.ALLOWED_STATUSES:
                self.logger.warning(
                    f"Entity {subscriber.technical_id} has invalid status"
                )
                return False

            self.logger.info(
                f"Entity {subscriber.technical_id} validation passed"
            )
            return True

        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return False

