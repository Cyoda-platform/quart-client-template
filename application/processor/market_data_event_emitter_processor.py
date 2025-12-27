import logging
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.market_data import MarketData


class MarketDataEventEmitterProcessor(CyodaProcessor):
    """
    Emits market data events to downstream pricing processors.
    Enables real-time updates across the trading platform.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataEventEmitterProcessor",
            description="Emits market data events to downstream processors",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Emit market data event.

        Args:
            entity: The MarketData entity to emit
            **kwargs: Additional parameters

        Returns:
            The entity after event emission
        """
        try:
            market_data = cast_entity(entity, MarketData)

            self.logger.info(
                f"Emitted event for {market_data.symbol}: bid={market_data.bid}, ask={market_data.ask}"
            )
            return market_data

        except Exception as e:
            self.logger.error(f"Error emitting market data event: {str(e)}")
            raise

