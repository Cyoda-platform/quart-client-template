"""
PositionUpdater processor for institutional trading platform.

Updates Position entities from executions and updates realized/unrealized P&L.
Used on execution_processing.transition 'apply' and position_valuation.transition 'calculate' (SYNC).
"""

import logging
from datetime import datetime, timezone
from typing import Any

from common.processor.base import CyodaEntity, CyodaProcessor


class PositionUpdater(CyodaProcessor):
    """
    Updates Position entities from executions and calculates P&L.
    """

    def __init__(self) -> None:
        super().__init__(
            name="PositionUpdater",
            description="Updates positions from executions and calculates P&L",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Update position from execution or market data.

        Args:
            entity: The execution or market_tick entity
            **kwargs: Additional update parameters

        Returns:
            The updated entity
        """
        try:
            entity_type = getattr(entity, "entity_type", None)
            self.logger.info(
                f"Updating position from {entity_type} {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Determine if this is an execution or market tick
            if entity_type == "execution" or hasattr(entity, "orderId"):
                await self._update_from_execution(entity)
            elif entity_type == "market_tick" or hasattr(entity, "instrumentId"):
                await self._update_from_market_tick(entity)

            self.logger.info(
                f"Position update completed for {getattr(entity, 'technical_id', '<unknown>')}"
            )
            return entity

        except Exception as e:
            self.logger.error(f"Error updating position: {str(e)}")
            raise

    async def _update_from_execution(self, entity: CyodaEntity) -> None:
        """
        Update position from an execution.

        Args:
            entity: The execution entity
        """
        # TODO: Integrate with position service
        # - Fetch current position for account/instrument
        # - Calculate new quantity (add/subtract based on side)
        # - Calculate new average price
        # - Calculate realized P&L if closing position
        # - Update position entity

        quantity = getattr(entity, "quantity", 0)
        price = getattr(entity, "price", 0)

        self.logger.debug(
            f"Updating position from execution: qty={quantity}, price={price}"
        )

        # Mock position update
        position_update = {
            "quantity_change": quantity,
            "price_change": price,
            "realized_pnl": 0,  # TODO: Calculate based on position direction
            "updated_at": (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            ),
        }

        if not hasattr(entity, "positionMetadata"):
            setattr(entity, "positionMetadata", {})
        position_metadata = getattr(entity, "positionMetadata")
        position_metadata.update(position_update)

    async def _update_from_market_tick(self, entity: CyodaEntity) -> None:
        """
        Update position unrealized P&L from market tick.

        Args:
            entity: The market_tick entity
        """
        # TODO: Integrate with position service
        # - Fetch all positions for the instrument
        # - Calculate unrealized P&L using new market price
        # - Update position entities

        instrument_id = getattr(entity, "instrumentId", None)
        last_price = getattr(entity, "lastPrice", 0)
        bid = getattr(entity, "bid", 0)
        ask = getattr(entity, "ask", 0)

        self.logger.debug(
            f"Updating positions for {instrument_id}: price={last_price}, bid={bid}, ask={ask}"
        )

        # Mock market data update
        market_update = {
            "last_price": last_price,
            "bid": bid,
            "ask": ask,
            "updated_at": (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            ),
        }

        if not hasattr(entity, "marketMetadata"):
            setattr(entity, "marketMetadata", {})
        market_metadata = getattr(entity, "marketMetadata")
        market_metadata.update(market_update)

    def _calculate_realized_pnl(
        self, quantity: float, entry_price: float, exit_price: float, side: str
    ) -> float:
        """
        Calculate realized P&L from a position close.

        Args:
            quantity: Quantity closed
            entry_price: Entry price
            exit_price: Exit price
            side: Original position side (BUY or SELL)

        Returns:
            Realized P&L
        """
        if side == "BUY":
            return quantity * (exit_price - entry_price)
        else:
            return quantity * (entry_price - exit_price)

    def _calculate_unrealized_pnl(
        self, quantity: float, entry_price: float, market_price: float, side: str
    ) -> float:
        """
        Calculate unrealized P&L for an open position.

        Args:
            quantity: Position quantity
            entry_price: Entry price
            market_price: Current market price
            side: Position side (BUY or SELL)

        Returns:
            Unrealized P&L
        """
        if side == "BUY":
            return quantity * (market_price - entry_price)
        else:
            return quantity * (entry_price - market_price)
