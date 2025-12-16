from common.processor.base import CyodaProcessor
from common.entity.cyoda_entity import CyodaEntity
from common.entity.entity_casting import cast_entity
from application.entity.market_data.version_1.market_data import MarketData
from services.services import get_entity_service
from datetime import datetime, timezone
import json
import logging

class MarketDataIngestProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="MarketDataIngestProcessor",
            description="Ingests and processes raw market data"
        )

    async def process(self, entity: CyodaEntity, **kwargs) -> MarketData:
        try:
            market_data = cast_entity(entity, MarketData)

            # Validate timestamp
            if not market_data.timestamp:
                market_data.timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            # Ensure historical prices exists
            market_data.historical_prices = market_data.historical_prices or []

            # Add current price to historical prices
            market_data.historical_prices.append({
                "price": market_data.price,
                "timestamp": market_data.timestamp
            })

            # Limit historical prices to last 10 entries
            market_data.historical_prices = market_data.historical_prices[-10:]

            self.logger.info(f"Ingested market data for symbol {market_data.symbol}")
            return market_data

        except Exception as e:
            self.logger.error(f"Error processing market data: {str(e)}")
            raise

class MarketDataBroadcastProcessor(CyodaProcessor):
    def __init__(self) -> None:
        super().__init__(
            name="MarketDataBroadcastProcessor",
            description="Broadcasts market data to subscribers"
        )

    async def process(self, entity: CyodaEntity, **kwargs) -> MarketData:
        try:
            market_data = cast_entity(entity, MarketData)
            entity_service = get_entity_service()

            # Here you would typically integrate with a messaging system
            # For now, we'll just log the broadcast
            broadcast_data = {
                "symbol": market_data.symbol,
                "price": market_data.price,
                "volume": market_data.volume,
                "timestamp": market_data.timestamp
            }

            self.logger.info(f"Broadcasting market data: {json.dumps(broadcast_data)}")

            return market_data

        except Exception as e:
            self.logger.error(f"Error broadcasting market data: {str(e)}")
            raise