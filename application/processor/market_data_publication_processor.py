"""
MarketDataPublicationProcessor for market data publication.

Publishes normalized market data to internal event bus.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.market_data_tick.version_1.market_data_tick import (
    MarketDataTick,
)
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class MarketDataPublicationProcessor(CyodaProcessor):
    """Publishes market data to internal event bus."""

    def __init__(self) -> None:
        super().__init__(name="MarketDataPublicationProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Publish market data.

        Args:
            entity: The market data tick entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed market data tick entity
        """
        try:
            self.logger.info(
                f"Publishing market data {getattr(entity, 'technical_id', '<unknown>')}"
            )

            tick = cast_entity(entity, MarketDataTick)

            # Publish to event bus (simulated)
            spread = tick.ask - tick.bid
            self.logger.info(
                f"Market data {tick.technical_id} published: {tick.instrument_id} "
                f"Bid={tick.bid} Ask={tick.ask} Spread={spread}"
            )

            return tick

        except Exception as e:
            self.logger.error(f"Error publishing market data: {str(e)}")
            raise
