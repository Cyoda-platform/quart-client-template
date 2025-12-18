"""
PositionProcessor for trading platform.

Handles position updates from trade execution and P&L calculations.
"""

import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.position.version_1.position import Position

logger = logging.getLogger(__name__)


class PositionProcessor(CyodaProcessor):
    """Processes position updates and P&L calculations."""

    def __init__(self) -> None:
        super().__init__(
            name="PositionProcessor",
            description="Handles position updates and P&L calculations",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process position entity and update P&L.

        Args:
            entity: The position entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed position entity
        """
        try:
            position = cast_entity(entity, Position)
            self.logger.info(f"Processing position {position.symbol}")

            # Recalculate P&L
            position.market_value = position.quantity * position.market_price
            position.unrealized_pnl = position.market_value - (position.quantity * position.avg_cost)
            position.total_pnl = position.unrealized_pnl + position.realized_pnl
            
            if position.quantity * position.avg_cost != 0:
                position.pnl_percent = (position.total_pnl / (position.quantity * position.avg_cost)) * 100
            else:
                position.pnl_percent = 0.0

            self.logger.info(f"Position {position.symbol} P&L updated: {position.total_pnl}")
            return position

        except Exception as e:
            self.logger.error(f"Error processing position: {str(e)}")
            raise

