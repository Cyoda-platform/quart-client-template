"""
PnLCalculationProcessor for real-time P&L calculations.

Calculates realized and unrealized P&L for positions.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.position.version_1.position import Position


class PnLCalculationProcessor(CyodaProcessor):
    """Calculates real-time P&L for positions."""

    def __init__(self) -> None:
        super().__init__(name="PnLCalculationProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Calculate P&L.

        Args:
            entity: The position entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed position entity
        """
        try:
            self.logger.info(f"Calculating P&L for position {getattr(entity, 'technical_id', '<unknown>')}")

            position = cast_entity(entity, Position)

            # Calculate unrealized P&L
            position.unrealized_pnl = position.quantity * (position.current_price - position.avg_cost)

            position.updated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            self.logger.info(f"Position {position.technical_id} P&L: {position.unrealized_pnl}")
            return position

        except Exception as e:
            self.logger.error(f"Error calculating P&L: {str(e)}")
            raise

