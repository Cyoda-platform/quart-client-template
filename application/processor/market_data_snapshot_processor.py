import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.market_data import MarketData


class MarketDataSnapshotProcessor(CyodaProcessor):
    """
    Stores latest market data snapshot for each symbol.
    Maintains current market state for real-time pricing.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataSnapshotProcessor",
            description="Stores latest market data snapshot",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Store market data snapshot.

        Args:
            entity: The MarketData entity to snapshot
            **kwargs: Additional parameters

        Returns:
            The entity with snapshot metadata
        """
        try:
            market_data = cast_entity(entity, MarketData)

            self.logger.info(
                f"Stored snapshot for {market_data.symbol} at {market_data.timestamp}"
            )
            return market_data

        except Exception as e:
            self.logger.error(f"Error storing market data snapshot: {str(e)}")
            raise

