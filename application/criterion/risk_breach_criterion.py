"""
RiskBreachCriterion for institutional trading platform.

Detects when risk metrics exceed breach thresholds (circuit breaker).
"""

from typing import Any

from application.entity.risk_metrics.version_1.risk_metrics import RiskMetrics
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class RiskBreachCriterion(CyodaCriteriaChecker):
    """
    Criterion for detecting risk breach conditions (circuit breaker).
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskBreachCriterion",
            description="Detects when risk metrics exceed breach thresholds",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if risk metrics exceed breach thresholds.

        Args:
            entity: The risk metrics entity to check
            **kwargs: Additional criteria parameters

        Returns:
            True if breach threshold is exceeded, False otherwise
        """
        try:
            self.logger.info(
                f"Checking risk breach {getattr(entity, 'technical_id', '<unknown>')}"
            )

            risk = cast_entity(entity, RiskMetrics)

            # Check position limit breach
            if risk.current_position > risk.position_limit:
                self.logger.error(
                    f"Position limit breach: {risk.current_position} > {risk.position_limit}"
                )
                return True

            # Check exposure limit breach
            if risk.current_exposure > risk.exposure_limit:
                self.logger.error(
                    f"Exposure limit breach: {risk.current_exposure} > {risk.exposure_limit}"
                )
                return True

            # Check margin breach
            if risk.available_margin < 0:
                self.logger.error("Margin breach: available margin is negative")
                return True

            self.logger.info("Risk metrics within acceptable limits")
            return False

        except Exception as e:
            entity_id = getattr(entity, "technical_id", "<unknown>")
            self.logger.error(
                f"Error checking risk breach {entity_id}: {str(e)}"
            )
            return False
