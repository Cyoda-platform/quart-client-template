"""
Risk validation criteria for the trading platform.

Validates risk profiles and compliance requirements.
"""

import logging
from typing import Any

from application.entity.risk_profile.version_1.risk_profile import RiskProfile
from common.criterion.base import CyodaCriterion, CyodaEntity
from common.entity.entity_casting import cast_entity


class RiskValidationCriterion(CyodaCriterion):
    """
    Criterion for validating risk profiles.

    Checks risk profile data and compliance requirements.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskValidationCriterion",
            description="Validates risk profile data and compliance",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def evaluate(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Evaluate risk validation criterion.

        Args:
            entity: The RiskProfile entity to validate
            **kwargs: Additional parameters

        Returns:
            True if risk profile is valid, False otherwise
        """
        try:
            self.logger.info(
                f"Validating risk profile {getattr(entity, 'technical_id', '<unknown>')}"
            )

            risk_profile = cast_entity(entity, RiskProfile)

            # Validate required fields
            if not risk_profile.risk_profile_id:
                self.logger.warning("Risk profile ID is missing")
                return False

            if not risk_profile.account_id:
                self.logger.warning("Account ID is missing")
                return False

            # Validate limits
            if risk_profile.max_notional <= 0:
                self.logger.warning("Max notional must be positive")
                return False

            if risk_profile.max_position <= 0:
                self.logger.warning("Max position must be positive")
                return False

            # Validate margin requirement
            if (
                risk_profile.margin_requirement <= 0
                or risk_profile.margin_requirement > 100
            ):
                self.logger.warning("Margin requirement must be between 0 and 100")
                return False

            self.logger.info(
                f"Risk profile {risk_profile.technical_id} validation passed"
            )
            return True

        except Exception as e:
            self.logger.error(
                f"Risk validation error for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False
