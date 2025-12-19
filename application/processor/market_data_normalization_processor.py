import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.market_data.version_1.market_data import MarketData


class MarketDataNormalizationProcessor(CyodaProcessor):
    """Normalizes market data from various venues to canonical format."""

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataNormalizationProcessor",
            description="Normalizes market data from venue-specific formats",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Normalize market data.

        Args:
            entity: The MarketData entity to process
            **kwargs: Additional processing parameters

        Returns:
            Normalized market data entity
        """
        try:
            market_data = cast_entity(entity, MarketData)

            self.logger.info(f"Normalizing market data {market_data.entity_id}")

            market_data.published_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

            self.logger.info(f"Market data {market_data.entity_id} normalized")
            return market_data

        except Exception as e:
            self.logger.error(f"Error normalizing market data: {str(e)}")
            raise

