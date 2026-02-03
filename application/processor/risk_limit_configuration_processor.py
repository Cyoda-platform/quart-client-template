"""
RiskLimitConfigurationProcessor for risk limit configuration.

Configures and validates risk limit parameters.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.risk_limit.version_1.risk_limit import RiskLimit
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class RiskLimitConfigurationProcessor(CyodaProcessor):
    """Configures risk limits for accounts."""

    def __init__(self) -> None:
        super().__init__(name="RiskLimitConfigurationProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Configure risk limit.

        Args:
            entity: The risk limit entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed risk limit entity
        """
        try:
            self.logger.info(
                f"Configuring risk limit {getattr(entity, 'technical_id', '<unknown>')}"
            )

            limit = cast_entity(entity, RiskLimit)

            # Validate limit configuration
            if limit.limit_value <= 0:
                raise ValueError("Limit value must be positive")

            if limit.current_usage > limit.limit_value:
                raise ValueError("Current usage cannot exceed limit value")

            self.logger.info(
                f"Risk limit {limit.technical_id} configured: {limit.limit_type}"
            )
            return limit

        except Exception as e:
            self.logger.error(f"Error configuring risk limit: {str(e)}")
            raise
