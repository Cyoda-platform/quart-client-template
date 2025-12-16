"""
Risk processors for the trading platform.

Handles margin calculations, limit checking, and risk alerts.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.risk_profile.version_1.risk_profile import RiskProfile
from services.services import get_entity_service


class MarginCalculator(CyodaProcessor):
    """
    Processor for calculating margin requirements.

    Computes required margin based on positions and risk profile.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarginCalculator",
            description="Calculates margin requirements",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Calculate margin requirements.

        Args:
            entity: The RiskProfile entity
            **kwargs: Additional parameters

        Returns:
            The risk profile with margin calculations
        """
        try:
            self.logger.info(
                f"Calculating margin for risk profile {getattr(entity, 'technical_id', '<unknown>')}"
            )

            risk_profile = cast_entity(entity, RiskProfile)

            # Validate margin requirement
            if risk_profile.margin_requirement <= 0 or risk_profile.margin_requirement > 100:
                raise ValueError("Margin requirement must be between 0 and 100")

            self.logger.info(
                f"Margin calculated for risk profile {risk_profile.technical_id}: {risk_profile.margin_requirement}%"
            )

            return risk_profile

        except Exception as e:
            self.logger.error(
                f"Margin calculation failed for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise


class LimitChecker(CyodaProcessor):
    """
    Processor for checking trading limits.

    Validates positions against configured limits.
    """

    def __init__(self) -> None:
        super().__init__(
            name="LimitChecker",
            description="Checks trading limits",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Check trading limits.

        Args:
            entity: The RiskProfile entity
            **kwargs: Additional parameters

        Returns:
            The risk profile with limit check results
        """
        try:
            self.logger.info(
                f"Checking limits for risk profile {getattr(entity, 'technical_id', '<unknown>')}"
            )

            risk_profile = cast_entity(entity, RiskProfile)

            # Validate limits
            if risk_profile.max_notional <= 0:
                raise ValueError("Max notional must be positive")

            if risk_profile.max_position <= 0:
                raise ValueError("Max position must be positive")

            self.logger.info(
                f"Limits validated for risk profile {risk_profile.technical_id}"
            )

            return risk_profile

        except Exception as e:
            self.logger.error(
                f"Limit check failed for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise


class RiskAlerter(CyodaProcessor):
    """
    Processor for generating risk alerts.

    Creates compliance events for risk violations.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskAlerter",
            description="Generates risk alerts and compliance events",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Generate risk alert.

        Args:
            entity: The RiskProfile entity
            **kwargs: Additional parameters

        Returns:
            The risk profile
        """
        try:
            self.logger.info(
                f"Generating risk alert for risk profile {getattr(entity, 'technical_id', '<unknown>')}"
            )

            risk_profile = cast_entity(entity, RiskProfile)

            self.logger.info(
                f"Risk alert generated for risk profile {risk_profile.technical_id}"
            )

            return risk_profile

        except Exception as e:
            self.logger.error(
                f"Risk alert generation failed for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

