"""
PnLCalculator processor for institutional trading platform.

Calculates realized and unrealized P&L for trades and positions.
"""

import logging
from typing import Any

from application.entity.position import Position
from application.entity.trade import Trade
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class PnLCalculator(CyodaProcessor):
    """
    Calculates P&L for trades and positions.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PnLCalculator",
            description="Calculates realized and unrealized P&L",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Calculate P&L for the entity (Trade or Position).

        Args:
            entity: The Trade or Position entity

        Returns:
            The entity with calculated P&L
        """
        try:
            entity_type = getattr(entity, "ENTITY_NAME", None)

            if entity_type == "Trade":
                return await self._calculate_trade_pnl(entity)
            elif entity_type == "Position":
                return await self._calculate_position_pnl(entity)
            else:
                self.logger.warning(f"Unknown entity type: {entity_type}")
                return entity

        except Exception as e:
            self.logger.error(
                f"Error calculating P&L for {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

    async def _calculate_trade_pnl(self, entity: CyodaEntity) -> CyodaEntity:
        """Calculate P&L for a trade."""
        trade = cast_entity(entity, Trade)
        self.logger.info(f"Calculating P&L for trade {trade.technical_id}")
        return trade

    async def _calculate_position_pnl(self, entity: CyodaEntity) -> CyodaEntity:
        """Calculate unrealized P&L for a position."""
        position = cast_entity(entity, Position)

        if position.current_price and position.quantity > 0:
            unrealized_pnl = (
                position.current_price - position.average_cost
            ) * position.quantity
            position.unrealized_pnl = unrealized_pnl

        self.logger.info(
            f"Calculated P&L for position {position.technical_id}: {position.unrealized_pnl}"
        )
        return position
