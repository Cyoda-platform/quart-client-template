"""
ClaimValidationCriterion for Cyoda Claims Platform

Validates that a Claim is ready for fraud check by checking validation errors.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity
from application.entity.claim import Claim


class ClaimValidationCriterion(CyodaCriteriaChecker):
    """
    Validation criterion for Claim that checks if the claim has passed
    all validation checks before proceeding to fraud detection.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ClaimValidationCriterion",
            description="Validates claim is ready for fraud check",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if the claim has no validation errors.

        Args:
            entity: The CyodaEntity to validate (expected to be Claim)
            **kwargs: Additional criteria parameters

        Returns:
            True if claim has no validation_errors, False otherwise
        """
        try:
            self.logger.info(
                f"Validating claim {getattr(entity, 'technical_id', '<unknown>')}"
            )

            claim = cast_entity(entity, Claim)

            if not claim.validation_errors:
                self.logger.info(
                    f"Claim {claim.technical_id} passed validation criterion"
                )
                return True
            else:
                self.logger.warning(
                    f"Claim {claim.technical_id} has validation errors: {claim.validation_errors}"
                )
                return False

        except Exception as e:
            self.logger.error(
                f"Error validating claim {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False

