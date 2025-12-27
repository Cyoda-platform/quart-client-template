import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.market_data import MarketData


class MarketDataNormalizationProcessor(CyodaProcessor):
    """
    Normalizes incoming market data to standard format.
    Ensures consistent field naming and data types across sources.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataNormalizationProcessor",
            description="Normalizes market data to standard format",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Normalize market data.

        Args:
            entity: The MarketData entity to normalize
            **kwargs: Additional parameters

        Returns:
            The normalized entity
        """
        try:
            market_data = cast_entity(entity, MarketData)

            market_data.symbol = market_data.symbol.upper()
            if market_data.bid_size is None:
                market_data.bid_size = 0
            if market_data.ask_size is None:
                market_data.ask_size = 0

            self.logger.info(f"Normalized market data for {market_data.symbol}")
            return market_data

        except Exception as e:
            self.logger.error(f"Error normalizing market data: {str(e)}")
            raise

