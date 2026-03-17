"""
PnlCalculationProcessor for institutional trading platform.

Calculates real-time P&L for positions.
"""

import logging
from datetime import datetime, timezone

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.position.version_1.position import Position

logger = logging.getLogger(__name__)


class PnlCalculationProcessor(CyodaProcessor):
    """
    Processor for calculating real-time P&L for positions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PnlCalculationProcessor",
            description="Calculates real-time P&L for positions",
        )

    async def process(self, entity: CyodaEntity, **kwargs) -> CyodaEntity:
        """
        Process P&L calculation.

        Args:
            entity: The position entity to calculate P&L for
            **kwargs: Additional processing parameters

        Returns:
            The position with updated P&L
        """
        try:
            self.logger.info(
                f"Calculating P&L for position {getattr(entity, 'technical_id', '<unknown>')}"
            )

            position = cast_entity(entity, Position)

            # Calculate unrealized P&L if current price is available
            if position.current_price:
                position.unrealized_pnl = position.calculate_unrealized_pnl(
                    position.current_price
                )
                position.notional_value = position.calculate_notional_value(
                    position.current_price
                )

            # Calculate total P&L
            realized = position.realized_pnl or 0.0
            unrealized = position.unrealized_pnl or 0.0
            position.total_pnl = realized + unrealized

            # Update timestamp
            position.last_updated_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(
                f"Position {position.position_id} P&L calculated: {position.total_pnl}"
            )

            return position

        except Exception as e:
            self.logger.error(
                f"Error calculating P&L {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

