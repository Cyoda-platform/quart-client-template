"""
FraudFlagCriterion for Cyoda Claims Platform

Checks if a Claim has a fraud alert flag set.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.claim import Claim


class FraudFlagCriterion(CyodaCriteriaChecker):
    """
    Criterion for checking if a Claim has been flagged for fraud.
    Returns True if fraud_alert_id is set, False otherwise.
    """

    def __init__(self) -> None:
        super().__init__(
            name="FraudFlagCriterion",
            description="Checks if claim has fraud alert",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the claim has a fraud alert flag.

        Args:
            entity: The CyodaEntity to check (expected to be Claim)
            **kwargs: Additional criteria parameters

        Returns:
            True if fraud_alert_id is set, False otherwise
        """
        try:
            self.logger.info(
                f"Checking fraud flag for claim {getattr(entity, 'technical_id', '<unknown>')}"
            )

            claim = cast_entity(entity, Claim)

            if claim.fraud_alert_id:
                self.logger.info(
                    f"Claim {claim.technical_id} has fraud alert {claim.fraud_alert_id}"
                )
                return True
            else:
                self.logger.debug(
                    f"Claim {claim.technical_id} has no fraud alert"
                )
                return False

        except Exception as e:
            self.logger.error(
                f"Error checking fraud flag for claim {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

