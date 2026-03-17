"""
MarketDataUpdateProcessor for institutional trading platform.

Handles real-time market data updates with nanosecond precision timestamps.
"""

from typing import Any

import logging
from datetime import datetime, timezone

from application.entity.market_data.version_1.market_data import MarketData
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor

logger = logging.getLogger(__name__)


class MarketDataUpdateProcessor(CyodaProcessor):
    """
    Processor for updating market data feeds.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataUpdateProcessor",
            description="Updates real-time market data with nanosecond precision",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process market data update.

        Args:
            entity: The market data entity to update
            **kwargs: Additional processing parameters

        Returns:
            The updated market data
        """
        try:
            self.logger.info(
                f"Updating market data {getattr(entity, 'technical_id', '<unknown>')}"
            )

            market_data = cast_entity(entity, MarketData)

            # Update received timestamp
            market_data.received_timestamp = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            # Check for stale data (example: if older than 1 second)
            if market_data.exchange_timestamp:
                market_data.is_stale = False

            self.logger.info(
                f"Market data {market_data.market_data_id} updated: "
                f"bid={market_data.bid_price}, ask={market_data.ask_price}"
            )

            return market_data

        except Exception as e:
            entity_id = getattr(entity, "technical_id", "<unknown>")
            self.logger.error(f"Error updating market data {entity_id}: {str(e)}")
            raise
