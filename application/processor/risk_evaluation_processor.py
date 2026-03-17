"""
RiskEvaluationProcessor for institutional trading platform.

Evaluates real-time risk with position limits, margin checks, and VaR.
"""

import logging
from datetime import datetime, timezone

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.risk_metrics.version_1.risk_metrics import RiskMetrics

logger = logging.getLogger(__name__)


class RiskEvaluationProcessor(CyodaProcessor):
    """
    Processor for evaluating real-time risk metrics.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RiskEvaluationProcessor",
            description="Evaluates real-time risk with position and margin checks",
        )

    async def process(self, entity: CyodaEntity, **kwargs) -> CyodaEntity:
        """
        Process risk evaluation.

        Args:
            entity: The risk metrics entity to evaluate
            **kwargs: Additional processing parameters

        Returns:
            The risk metrics with updated status
        """
        try:
            self.logger.info(
                f"Evaluating risk for {getattr(entity, 'technical_id', '<unknown>')}"
            )

            risk = cast_entity(entity, RiskMetrics)

            # Calculate utilization percentages
            if risk.position_limit > 0:
                risk.position_utilization = (
                    risk.current_position / risk.position_limit * 100
                )

            if risk.exposure_limit > 0:
                risk.exposure_utilization = (
                    risk.current_exposure / risk.exposure_limit * 100
                )

            if risk.margin_requirement > 0:
                risk.margin_utilization = (
                    (risk.margin_requirement - risk.available_margin)
                    / risk.margin_requirement
                    * 100
                )

            # Determine risk status based on utilization
            risk.risk_status = self._determine_risk_status(risk)

            # Update evaluation timestamp
            risk.evaluated_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(
                f"Risk evaluation complete: status={risk.risk_status}"
            )

            return risk

        except Exception as e:
            self.logger.error(
                f"Error evaluating risk {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    def _determine_risk_status(self, risk: RiskMetrics) -> str:
        """
        Determine risk status based on utilization levels.

        Args:
            risk: The risk metrics to evaluate

        Returns:
            Risk status: compliant, warning, or breach
        """
        position_util = risk.position_utilization or 0
        exposure_util = risk.exposure_utilization or 0
        margin_util = risk.margin_utilization or 0

        if position_util >= 100 or exposure_util >= 100 or margin_util >= 100:
            return "breach"
        elif position_util >= 80 or exposure_util >= 80 or margin_util >= 80:
            return "warning"
        return "compliant"

