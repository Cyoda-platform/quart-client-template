"""
RiskLimitMonitoringProcessor for risk limit monitoring.

Monitors risk limit usage and triggers alerts on breaches.
"""

import logging
from typing import Any

from application.entity.risk_limit.version_1.risk_limit import RiskLimit
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class RiskLimitMonitoringProcessor(CyodaProcessor):
    """Monitors risk limit usage."""

    def __init__(self) -> None:
        super().__init__(name="RiskLimitMonitoringProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Monitor risk limit.

        Args:
            entity: The risk limit entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed risk limit entity
        """
        try:
            self.logger.info(
                f"Monitoring risk limit {getattr(entity, 'technical_id', '<unknown>')}"
            )

            limit = cast_entity(entity, RiskLimit)

            # Check usage percentage
            usage_pct = (
                (limit.current_usage / limit.limit_value) * 100
                if limit.limit_value > 0
                else 0
            )

            if usage_pct > 90:
                self.logger.warning(
                    f"Risk limit {limit.technical_id} at {usage_pct:.1f}% utilization"
                )

            self.logger.info(
                f"Risk limit {limit.technical_id} monitored: {usage_pct:.1f}% used"
            )
            return limit

        except Exception as e:
            self.logger.error(f"Error monitoring risk limit: {str(e)}")
            raise
