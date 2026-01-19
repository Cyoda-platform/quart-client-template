"""
FraudDeterminationCriterion for Cyoda Claims Platform

Checks if a FraudAlert investigation is complete.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.fraud_alert import FraudAlert


class FraudDeterminationCriterion(CyodaCriteriaChecker):
    """
    Criterion for checking if a FraudAlert investigation is complete.
    Returns True if investigation_notes has entries, False otherwise.
    """

    def __init__(self) -> None:
        super().__init__(
            name="FraudDeterminationCriterion",
            description="Checks if fraud investigation is complete",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the fraud alert investigation is complete.

        Args:
            entity: The CyodaEntity to check (expected to be FraudAlert)
            **kwargs: Additional criteria parameters

        Returns:
            True if investigation_notes has entries, False otherwise
        """
        try:
            self.logger.info(
                f"Checking investigation status for alert {getattr(entity, 'technical_id', '<unknown>')}"
            )

            fraud_alert = cast_entity(entity, FraudAlert)

            if fraud_alert.investigation_notes:
                self.logger.info(
                    f"FraudAlert {fraud_alert.technical_id} has {len(fraud_alert.investigation_notes)} investigation notes"
                )
                return True
            else:
                self.logger.debug(
                    f"FraudAlert {fraud_alert.technical_id} has no investigation notes"
                )
                return False

        except Exception as e:
            self.logger.error(
                f"Error checking investigation status for alert {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False
