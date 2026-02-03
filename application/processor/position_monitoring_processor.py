"""
PositionMonitoringProcessor for position monitoring.

Monitors positions for risk and compliance.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.position.version_1.position import Position


class PositionMonitoringProcessor(CyodaProcessor):
    """Monitors positions for risk and compliance."""

    def __init__(self) -> None:
        super().__init__(name="PositionMonitoringProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Monitor position.

        Args:
            entity: The position entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed position entity
        """
        try:
            self.logger.info(f"Monitoring position {getattr(entity, 'technical_id', '<unknown>')}")

            position = cast_entity(entity, Position)

            # Check position limits
            position_value = abs(position.quantity * position.current_price)
            if position_value > 100000000:  # $100M limit
                self.logger.warning(f"Position {position.technical_id} exceeds size limit")

            position.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            self.logger.info(f"Position {position.technical_id} monitored")
            return position

        except Exception as e:
            self.logger.error(f"Error monitoring position: {str(e)}")
            raise

