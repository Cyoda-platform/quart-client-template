"""
UpdatePositionPnLProcessor for trading platform.

Handles calculation and update of Position P&L by retrieving current
market data and computing unrealized profit and loss.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.market_data.version_1.market_data import MarketData
from application.entity.position.version_1.position import Position
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class UpdatePositionPnLProcessor(CyodaProcessor):
    """
    Processor for Position that updates P&L calculations.

    Retrieves latest MarketData for the position's instrument and calculates
    unrealized P&L based on current market prices vs. average entry price.
    """

    def __init__(self) -> None:
        super().__init__(
            name="UpdatePositionPnLProcessor",
            description=(
                "Updates Position P&L by calculating unrealized "
                "gains/losses from market data"
            ),
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the Position entity and update P&L calculations.

        Args:
            entity: The Position entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed Position entity with updated P&L
        """
        try:
            self.logger.info(
                f"Processing Position {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to Position for type-safe operations
            position = cast_entity(entity, Position)

            # Get entity service
            entity_service = get_entity_service()

            # Retrieve latest market data for the instrument
            market_data = await self._get_latest_market_data(
                entity_service, position.instrument_id
            )

            if market_data is None:
                self.logger.warning(
                    f"No market data available for instrument {position.instrument_id} - "
                    f"skipping P&L update"
                )
                return position

            # Calculate unrealized P&L
            self._calculate_unrealized_pnl(position, market_data)

            # Update timestamp
            position.last_updated = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(
                f"Position {position.technical_id} P&L updated - "
                f"current_price: {position.current_price}, "
                f"unrealized_pnl: {position.unrealized_pnl:.2f}"
            )

            return position

        except Exception as e:
            error_id = getattr(entity, 'technical_id', '<unknown>')
            self.logger.error(
                f"Error processing Position {error_id}: {str(e)}"
            )
            raise

    async def _get_latest_market_data(
        self, entity_service: Any, instrument_id: str
    ) -> MarketData | None:
        """
        Retrieve the latest market data for the instrument.

        Args:
            entity_service: The entity service instance
            instrument_id: The instrument ID to get market data for

        Returns:
            MarketData entity or None if not found
        """
        try:
            # Note: In a real system, you would use proper query filters
            # to retrieve the latest market data for the instrument
            # For this example, we'll return None and log
            self.logger.info(
                f"Retrieving latest market data for instrument {instrument_id}"
            )

            # Placeholder - in production, implement proper query to get latest market data
            # For now, return None to indicate no market data available
            return None

        except Exception as e:
            self.logger.error(
                f"Error retrieving market data for instrument {instrument_id}: {str(e)}"
            )
            return None

    def _calculate_unrealized_pnl(
        self, position: Position, market_data: MarketData
    ) -> None:
        """
        Calculate unrealized P&L for the position.

        Formula: (current_price - average_price) * quantity

        Args:
            position: The Position entity to update
            market_data: The latest MarketData for the instrument
        """
        # Determine current price from market data
        # Prefer last_price, fall back to mid-price if available
        current_price = market_data.last_price

        if current_price is None:
            # Calculate mid-price if bid/ask available
            if market_data.bid is not None and market_data.ask is not None:
                current_price = (market_data.bid + market_data.ask) / 2.0
            else:
                self.logger.warning(
                    f"No usable price in market data for instrument {position.instrument_id}"
                )
                return

        # Update position's current price
        position.current_price = current_price

        # Calculate unrealized P&L
        # Formula: (current_price - average_price) * quantity
        price_diff = current_price - position.average_price
        unrealized_pnl = price_diff * position.quantity

        # Update position
        position.unrealized_pnl = unrealized_pnl

        self.logger.info(
            f"Calculated unrealized P&L for position {position.technical_id}: "
            f"quantity={position.quantity}, avg_price={position.average_price:.4f}, "
            f"current_price={current_price:.4f}, unrealized_pnl={unrealized_pnl:.2f}"
        )
