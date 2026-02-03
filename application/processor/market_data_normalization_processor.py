"""
MarketDataNormalizationProcessor for market data normalization.

Normalizes market data from different venues to internal schema.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.market_data_tick.version_1.market_data_tick import (
    MarketDataTick,
)
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class MarketDataNormalizationProcessor(CyodaProcessor):
    """Normalizes market data to internal schema."""

    def __init__(self) -> None:
        super().__init__(name="MarketDataNormalizationProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Normalize market data.

        Args:
            entity: The market data tick entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed market data tick entity
        """
        try:
            self.logger.info(
                f"Normalizing market data {getattr(entity, 'technical_id', '<unknown>')}"
            )

            tick = cast_entity(entity, MarketDataTick)

            # Normalize venue names
            venue_map = {
                "NYSE": "NYSE",
                "NASDAQ": "NASDAQ",
                "CBOE": "CBOE",
                "SIP": "SIP",
            }
            tick.venue = venue_map.get(tick.venue, tick.venue)

            self.logger.info(f"Market data {tick.technical_id} normalized")
            return tick

        except Exception as e:
            self.logger.error(f"Error normalizing market data: {str(e)}")
            raise
