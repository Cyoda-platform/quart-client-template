"""
RiskWarningCriterion for institutional trading platform.

Detects when risk metrics trigger warning thresholds.
"""

from typing import Any

from application.entity.risk_metrics.version_1.risk_metrics import RiskMetrics
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaCriteriaChecker, CyodaEntity


class RiskWarningCriterion(CyodaCriteriaChecker):
    """
    Criterion for detecting risk warning conditions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskWarningCriterion",
            description="Detects when risk metrics trigger warning thresholds",
        )

    async def check(self, entity: CyodaEntity, **kwargs: Any) -> bool:
        """
        Check if risk metrics trigger warning conditions.

        Args:
            entity: The risk metrics entity to check
            **kwargs: Additional criteria parameters

        Returns:
            True if warning threshold is triggered, False otherwise
        """
        try:
            self.logger.info(
                f"Checking risk warning {getattr(entity, 'technical_id', '<unknown>')}"
            )

            risk = cast_entity(entity, RiskMetrics)

            # Check position utilization
            position_util = risk.position_utilization or 0
            if position_util >= 80:
                self.logger.warning(f"Position utilization warning: {position_util}%")
                return True

            # Check exposure utilization
            exposure_util = risk.exposure_utilization or 0
            if exposure_util >= 80:
                self.logger.warning(f"Exposure utilization warning: {exposure_util}%")
                return True

            # Check margin utilization
            margin_util = risk.margin_utilization or 0
            if margin_util >= 80:
                self.logger.warning(f"Margin utilization warning: {margin_util}%")
                return True

            self.logger.info("Risk metrics within normal thresholds")
            return False

        except Exception as e:
            self.logger.error(
                f"Error checking risk warning {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            return False
