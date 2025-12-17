import logging
from datetime import datetime, timezone
from typing import Any

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor
from application.entity.market_data.version_1.market_data import MarketData


class MarketDataProcessor(CyodaProcessor):
    """
    Processor for MarketData that handles data normalization and enrichment.
    """

    def __init__(self) -> None:
        super().__init__(
            name="MarketDataProcessor",
            description="Processes MarketData instances and normalizes feed formats",
        )
        self.logger: logging.Logger = getattr(
            self, "logger", logging.getLogger(__name__)
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Process the MarketData for normalization.

        Args:
            entity: The MarketData to process
            **kwargs: Additional processing parameters

        Returns:
            The processed market data with normalized values
        """
        try:
            self.logger.info(
                f"Processing MarketData {getattr(entity, 'technical_id', '<unknown>')}"
            )

            market_data = cast_entity(entity, MarketData)

            market_data.normalized_at = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )
            market_data.status = "NORMALIZED"

            self.logger.info(
                f"MarketData for {market_data.instrument} normalized successfully"
            )

            return market_data

        except Exception as e:
            self.logger.error(
                f"Error processing market data {getattr(entity, 'technical_id', '<unknown>')}: {str(e)}"
            )
            raise

