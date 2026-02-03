"""
MarketDataIngestionProcessor for market data ingestion.

Ingests and validates market data from multiple venues.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from application.entity.market_data_tick.version_1.market_data_tick import (
    MarketDataTick,
)
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


class MarketDataIngestionProcessor(CyodaProcessor):
    """Ingests market data from venues."""

    def __init__(self) -> None:
        super().__init__(name="MarketDataIngestionProcessor")
        self.logger = logging.getLogger(__name__)

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Ingest market data.

        Args:
            entity: The market data tick entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed market data tick entity
        """
        try:
            self.logger.info(
                f"Ingesting market data {getattr(entity, 'technical_id', '<unknown>')}"
            )

            tick = cast_entity(entity, MarketDataTick)

            # Validate bid-ask spread
            if tick.bid > tick.ask:
                raise ValueError("Bid price cannot exceed ask price")

            self.logger.info(
                f"Market data {tick.technical_id} ingested from {tick.venue}"
            )
            return tick

        except Exception as e:
            self.logger.error(f"Error ingesting market data: {str(e)}")
            raise
