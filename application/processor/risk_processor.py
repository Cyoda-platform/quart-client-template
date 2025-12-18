"""
RiskProcessor for trading platform.

Handles risk limit monitoring and alert generation.
"""

import logging
from typing import Any

from application.entity.risk_limit.version_1.risk_limit import RiskLimit
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor

logger = logging.getLogger(__name__)


class RiskProcessor(CyodaProcessor):
    """Processes risk limits and generates alerts."""

    def __init__(self) -> None:
        super().__init__(
            name="RiskProcessor",
            description="Handles risk limit monitoring",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process risk limit entity and update usage.

        Args:
            entity: The risk limit entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed risk limit entity
        """
        try:
            limit = cast_entity(entity, RiskLimit)
            self.logger.info(f"Processing risk limit {limit.limit_type}")

            # Update usage percentage
            if limit.limit_value > 0:
                limit.usage_percent = (limit.current_usage / limit.limit_value) * 100
            else:
                limit.usage_percent = 0.0

            # Log if breached
            if limit.is_breached():
                self.logger.warning(
                    f"Risk limit {limit.limit_type} BREACHED: {limit.usage_percent}%"
                )
            elif limit.is_warning():
                self.logger.warning(
                    f"Risk limit {limit.limit_type} WARNING: {limit.usage_percent}%"
                )

            return limit

        except Exception as e:
            self.logger.error(f"Error processing risk limit: {str(e)}")
            raise
