"""
NormalizeMarketDataProcessor for trading platform.

Handles normalization of MarketData entities by calculating bid-ask spreads
and enriching market data with normalized metrics.
"""

import logging
from typing import Any

from application.entity.market_data.version_1.market_data import MarketData
from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from services.services import get_entity_service


class NormalizeMarketDataProcessor(CyodaProcessor):
    """
    Processor for MarketData that normalizes market data.

    Calculates bid-ask spread and enriches market data with normalized metrics
    for downstream processing and analytics.
    """

    def __init__(self) -> None:
        super().__init__(
            name="NormalizeMarketDataProcessor",
            description="Normalizes MarketData entities by calculating bid-ask spreads",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the MarketData entity to calculate normalized metrics.

        Args:
            entity: The MarketData entity to process
            **kwargs: Additional processing parameters

        Returns:
            The processed entity with normalized data
        """
        try:
            self.logger.info(
                f"Processing MarketData {getattr(entity, 'technical_id', '<unknown>')}"
            )

            # Cast the entity to MarketData for type-safe operations
            market_data = cast_entity(entity, MarketData)

            # Calculate normalized bid-ask spread if bid and ask are available
            if market_data.bid is not None and market_data.ask is not None:
                spread = market_data.ask - market_data.bid
                mid_price = (market_data.bid + market_data.ask) / 2.0

                # Avoid division by zero
                normalized_spread = (spread / mid_price) if mid_price != 0 else 0.0

                self.logger.info(
                    f"MarketData {market_data.technical_id} normalized - "
                    f"spread: {spread:.4f}, mid_price: {mid_price:.4f}, "
                    f"normalized_spread: {normalized_spread:.6f}"
                )
            else:
                self.logger.warning(
                    f"MarketData {market_data.technical_id} missing bid or ask - "
                    f"skipping normalization"
                )

            self.logger.info(
                f"MarketData {market_data.technical_id} processed successfully"
            )

            return market_data

        except Exception as e:
            self.logger.error(
                f"Error processing MarketData {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise
