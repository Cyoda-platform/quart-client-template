"""
WeeklySendBatchReadyCriterion for checking if email batches are ready.

Validates that an EmailSend entity has prepared batches and is ready
for the sending phase.
"""

from typing import Any

from application.entity.email_send.version_1.email_send import EmailSend
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class WeeklySendBatchReadyCriterion(CyodaCriteriaChecker):
    """
    Criterion for checking if email batches are ready for sending.
    """

    def __init__(self) -> None:
        super().__init__(
            name="WeeklySendBatchReadyCriterion",
            description="Checks if email batches are ready for sending",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the EmailSend entity has batches ready.

        Args:
            entity: The CyodaEntity to check (expected to be EmailSend)
            **kwargs: Additional criteria parameters

        Returns:
            True if batches are ready, False otherwise
        """
        try:
            self.logger.info(
                f"Checking batch readiness for {getattr(entity, 'technical_id', '<unknown>')}"
            )

            email_send = cast_entity(entity, EmailSend)

            # Check if total_recipients is set (batches prepared)
            if email_send.total_recipients <= 0:
                self.logger.warning(
                    f"Entity {email_send.technical_id} has no recipients"
                )
                return False

            # Check if status is in_progress
            if email_send.status != "in_progress":
                self.logger.warning(
                    f"Entity {email_send.technical_id} is not in_progress"
                )
                return False

            self.logger.info(f"Entity {email_send.technical_id} batches are ready")
            return True

        except Exception as e:
            self.logger.error(f"Batch readiness check error: {str(e)}")
            return False
