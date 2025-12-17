from common.processor.base import CyodaProcessor
from common.entity.cyoda_entity import CyodaEntity
from common.entity.entity_casting import cast_entity
from application.entity.market_data.version_1.market_data import MarketData
import logging

from typing import Any
class MarketDataIngestionProcessor(CyodaProcessor):
    """
    Processor for ingesting market data.
    """
    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Processes the market data entity.
        """
        market_data = cast_entity(entity, MarketData)
        logging.info(f"Processing market data for instrument: {market_data.instrument_id}")
        # In a real implementation, we would perform validation and normalization here.
        return market_data
