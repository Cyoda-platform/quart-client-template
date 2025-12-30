"""
RiskChecker processor for institutional trading platform.

Validates risk limits and controls.
"""

import logging
from typing import Any

from application.entity.risk_profile import RiskProfile
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class RiskChecker(CyodaProcessor):
    """
    Checks and validates risk limits for accounts.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskChecker",
            description="Validates risk limits and controls",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Check risk limits for the risk profile.

        Args:
            entity: The RiskProfile entity

        Returns:
            The risk profile with updated breach status
        """
        try:
            self.logger.info(
                f"Checking risk limits for {getattr(entity, 'technical_id', '<unknown>')}"
            )

            risk_profile = cast_entity(entity, RiskProfile)

            # Check if limits are breached
            is_breached = self._check_limits(risk_profile)

            if is_breached:
                risk_profile.breach_count += 1
                self.logger.warning(
                    f"Risk limit breach detected for {risk_profile.technical_id}"
                )

            return risk_profile

        except Exception as e:
            self.logger.error(
                f"Error checking risk limits for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _check_limits(self, risk_profile: RiskProfile) -> bool:
        """
        Check if any risk limits are breached.

        Args:
            risk_profile: The risk profile

        Returns:
            True if any limit is breached, False otherwise
        """
        # Check daily loss limit
        if risk_profile.current_loss >= risk_profile.max_daily_loss:
            return True

        return False
